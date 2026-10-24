from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping

from backend.app.funds.analysis_engine import FundAnalysisResult
from backend.app.funds.erste_hungary_evidence_surface import (
    erste_hungary_evidence_as_of,
    erste_hungary_evidence_rows,
    load_erste_hungary_evidence_surface,
)
from backend.app.funds.fund_auto_refresh import auto_refresh_selected_fund_if_due
from backend.app.funds.fund_profile_nonblocking_refresh import (
    queue_selected_fund_auto_refresh,
)
from backend.app.funds.fund_profile import build_fund_profile_read_model
from backend.app.funds.store import fund_observation_store
from backend.app.funds.free_float_store import (
    FreeFloatSourceError,
    default_free_float_store,
    free_float_records_from_bytes,
)
from backend.app.funds.kap_portfolio_auto_ingestion import (
    auto_ingest_kap_portfolio_reports,
)
from backend.app.funds.kap_free_float_auto_population import (
    KapFreeFloatError,
    MAX_FDO_SYMBOLS_PER_REFRESH,
    populate_kap_free_float_for_symbols,
)
from backend.app.funds.kap_portfolio_ingestion import (
    KapFundPortfolioError,
    ingest_kap_portfolio_pdf_upload,
    ingest_kap_portfolio_report_url,
)
from backend.app.funds.portfolio_tracking import (
    FundPortfolioChangeSet,
    FundPortfolioSnapshot,
    FundPortfolioSnapshotJsonStore,
    PortfolioPositionChange,
    PortfolioSnapshotStoreError,
    PositionChangeKind,
    StockFundActivity,
    aggregate_stock_fund_activity,
    compare_portfolio_snapshots,
)
from backend.app.funds.pressure_risk import StockFundPressureInput, StockFundPressureProfile
from backend.app.funds.pressure_read_model import build_fund_pressure_read_model


@dataclass(frozen=True, slots=True)
class FundPortfolioTrackingReadModel:
    latest_by_fund: Mapping[str, FundPortfolioSnapshot]
    changes_by_fund: Mapping[str, FundPortfolioChangeSet]
    stock_activity: tuple[StockFundActivity, ...]


def _fund_metadata_entry(
    fund_metadata: Mapping[str, Mapping[str, str]] | None,
    fund_id: str,
) -> Mapping[str, str]:
    if not fund_metadata:
        return {}
    return fund_metadata.get(fund_id, {})


def _fund_display_label(
    fund_id: str,
    fund_metadata: Mapping[str, Mapping[str, str]] | None = None,
) -> str:
    meta = _fund_metadata_entry(fund_metadata, fund_id)
    code = str(meta.get("fund_code") or fund_id.rsplit(":", 1)[-1]).strip()
    name = str(meta.get("fund_name") or "").strip()
    return f"{code} - {name}" if name else code


def _fund_category_label(
    fund_id: str,
    fallback: str | None,
    fund_metadata: Mapping[str, Mapping[str, str]] | None = None,
) -> str:
    meta = _fund_metadata_entry(fund_metadata, fund_id)
    return str(meta.get("category_name") or fallback or "EЕћLEЕћMEMД°Ећ").strip()


def fund_analysis_rows(
    results: Iterable[FundAnalysisResult],
    fund_metadata: Mapping[str, Mapping[str, str]] | None = None,
) -> tuple[dict[str, object], ...]:
    return tuple({
        "Fon": _fund_display_label(item.canonical_fund_id, fund_metadata),
        "Kategori": _fund_category_label(item.canonical_fund_id, item.category_id, fund_metadata),
        "S\u0131n\u0131f": item.classification.value,
        "Durum": item.class_label,
        "Pozitif": ", ".join(item.positive_families) or "-",
        "N\u00f6tr": ", ".join(item.neutral_families) or "-",
        "Dikkat": ", ".join(item.caution_families) or "-",
        "Eksik": ", ".join(item.unavailable_families) or "-",
        "Gerek\u00e7e": item.eligibility_reason,
    } for item in sorted(
        results,
        key=lambda x: (x.classification.value, x.canonical_fund_id),
    ))


def _decimal_display(value: Decimal | None, *, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _percent_display(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return _decimal_display(value * Decimal("100"))


def _latest_series_by_fund(
    snapshots: Iterable[FundPortfolioSnapshot],
) -> tuple[dict[str, FundPortfolioSnapshot], dict[str, FundPortfolioChangeSet]]:
    grouped: dict[str, list[FundPortfolioSnapshot]] = {}
    for snapshot in snapshots:
        grouped.setdefault(snapshot.canonical_fund_id, []).append(snapshot)

    latest_by_fund: dict[str, FundPortfolioSnapshot] = {}
    changes_by_fund: dict[str, FundPortfolioChangeSet] = {}
    for fund_id, candidates in grouped.items():
        latest = max(
            candidates,
            key=lambda item: (item.portfolio_date, item.publication_date, item.ingested_at, item.provider),
        )
        latest_by_fund[fund_id] = latest
        same_provider = sorted(
            (item for item in candidates if item.provider == latest.provider),
            key=lambda item: (item.portfolio_date, item.publication_date, item.ingested_at),
        )
        if len(same_provider) >= 2:
            changes_by_fund[fund_id] = compare_portfolio_snapshots(
                same_provider[-2],
                same_provider[-1],
            )
    return latest_by_fund, changes_by_fund


def build_fund_portfolio_tracking_read_model(
    store: FundPortfolioSnapshotJsonStore,
) -> FundPortfolioTrackingReadModel:
    snapshots = store.list_snapshots()
    latest_by_fund, changes_by_fund = _latest_series_by_fund(snapshots)
    return FundPortfolioTrackingReadModel(
        latest_by_fund=latest_by_fund,
        changes_by_fund=changes_by_fund,
        stock_activity=aggregate_stock_fund_activity(changes_by_fund.values()),
    )


def current_portfolio_rows(snapshot: FundPortfolioSnapshot) -> tuple[dict[str, object], ...]:
    positions = sorted(
        snapshot.positions,
        key=lambda item: (
            item.portfolio_weight is None,
            -(item.portfolio_weight or Decimal("0")),
            item.asset_type,
            item.symbol,
        ),
    )
    return tuple(
        {
            "Sembol": item.symbol,
            "Varlık Türü": item.asset_type,
            "Varlık": item.asset_name or "-",
            "Adet": _decimal_display(item.shares_held, digits=4),
            "Piyasa Değeri": _decimal_display(item.market_value),
            "Portföy %": _percent_display(item.portfolio_weight),
        }
        for item in positions
    )


def portfolio_change_rows(change_set: FundPortfolioChangeSet) -> tuple[dict[str, object], ...]:
    labels = {
        PositionChangeKind.NEW_ENTRY: "Yeni giriş",
        PositionChangeKind.INCREASED: "Artırıldı",
        PositionChangeKind.REDUCED: "Azaltıldı",
        PositionChangeKind.FULL_EXIT: "Tam çıkış",
        PositionChangeKind.UNCHANGED: "Değişmedi",
        PositionChangeKind.UNKNOWN: "Belirsiz",
    }
    return tuple(
        {
            "Hisse": item.symbol,
            "Durum": labels[item.kind],
            "Güven": item.confidence.value,
            "Önceki Adet": _decimal_display(item.previous_shares, digits=4),
            "Güncel Adet": _decimal_display(item.current_shares, digits=4),
            "Adet Değişimi": _decimal_display(item.share_change, digits=4),
            "Önceki %": _percent_display(item.previous_weight),
            "Güncel %": _percent_display(item.current_weight),
            "Ağırlık Δ pp": _decimal_display(item.weight_change_percentage_points),
            "Kanıt": item.reason,
        }
        for item in change_set.changes
    )


def stock_fund_activity_rows(items: Iterable[StockFundActivity]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Hisse": item.symbol,
            "Fon": item.current_fund_count,
            "Karşılaştırılabilir": item.comparable_fund_count,
            "Yeni": item.new_fund_count,
            "Tam Çıkış": item.exited_fund_count,
            "Artıran": item.increasing_fund_count,
            "Azaltan": item.decreasing_fund_count,
            "Belirsiz": item.unknown_fund_count,
            "Birikim Breadth %": _percent_display(item.accumulation_breadth),
            "Dağıtım Breadth %": _percent_display(item.distribution_breadth),
        }
        for item in items
    )



def _safe_float_display(value: object, *, scale: float = 1.0, digits: int = 6) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value) * scale, digits)
    except (TypeError, ValueError, OverflowError):
        return None

def fund_pressure_rows(
    profiles: Mapping[str, StockFundPressureProfile],
    inputs: Mapping[str, StockFundPressureInput] | None = None,
) -> tuple[dict[str, object], ...]:
    inputs = inputs or {}
    rows: list[dict[str, object]] = []
    for symbol, profile in sorted(profiles.items()):
        raw = inputs.get(symbol)
        rows.append({
            "Hisse": symbol,
            "Fon/FDO %": None if raw is None else _safe_float_display(raw.ownership.fund_free_float_ratio, scale=100.0),
            "Likidasyon Normal (gün)": None if raw is None else _safe_float_display(raw.liquidity.liquidation_days_normal),
            "Likidasyon Agresif (gün)": None if raw is None else _safe_float_display(raw.liquidity.liquidation_days_aggressive),
            "Likidasyon Stres (gün)": None if raw is None else _safe_float_display(raw.liquidity.liquidation_days_stress),
            "Fon Yoğunluğu": _decimal_display(profile.fund_concentration_risk.score),
            "Çıkış Zorluğu": _decimal_display(profile.exit_difficulty_risk.score),
            "Aktif Satış Baskısı": _decimal_display(profile.active_selling_pressure.score),
            "Veri Kalitesi": profile.data_quality_state.value,
            "Trade Authority": profile.automatic_trade_authority,
        })
    return tuple(rows)



def _profile_percent(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.2f}%"


def _profile_number(value: Decimal | None, *, digits: int = 4) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.{digits}f}"


def _render_selected_fund_profile(
    st: Any,
    *,
    fund_ids: tuple[str, ...],
    portfolio_store: FundPortfolioSnapshotJsonStore,
    fund_metadata: Mapping[str, Mapping[str, str]] | None = None,
) -> str | None:
    if not fund_ids:
        st.info("Fon profili için TEFAS evreni veya kayıtlı fon snapshot'ı bekleniyor.")
        return None

    st.markdown("### Fon Profili")
    st.caption(
        "Fintables benzeri tek-fon görünümüdür. Seçilen fonun TEFAS fiyat/genel durum verisi "
        "ve KAP portföyü yerel canonical depolardan okunur; veri zamanı dolduğunda sistem "
        "seçili fonu otomatik ve bounded olarak yeniler."
    )
    selected_key = "fund_profile_selected_fund"
    label_to_id = {
        _fund_display_label(fund_id, fund_metadata): fund_id
        for fund_id in fund_ids
    }
    display_options = tuple(label_to_id)
    if hasattr(st, "session_state"):
        previous = st.session_state.get(selected_key)
        if previous not in display_options:
            st.session_state.pop(selected_key, None)
    selected_label = st.selectbox(
        "Fon se\u00e7",
        options=display_options,
        index=0,
        key=selected_key,
    )
    selected = label_to_id[selected_label]
    code = selected.rsplit(":", 1)[-1]

    if hasattr(st, "session_state"):
        refresh_state = queue_selected_fund_auto_refresh(
            code,
            loader=lambda: auto_refresh_selected_fund_if_due(
                code,
                observation_store=fund_observation_store(),
                portfolio_store=portfolio_store,
                network_enabled=True,
            ),
            timeout_seconds=12.0,
        )
        if refresh_state.status == "RUNNING":
            st.caption(
                "Fon verisi arka planda güncelleniyor; son kayıtlı canonical veri gösteriliyor."
            )
        elif refresh_state.status == "FAILED" and hasattr(st, "warning"):
            st.warning(
                "Otomatik fon yenilemesi izole edildi; son iyi veri gösteriliyor. "
                + (refresh_state.error or "Bilinmeyen yenileme hatası")
            )
        elif refresh_state.status == "TIMEOUT" and hasattr(st, "warning"):
            st.warning(
                "Otomatik fon yenilemesi zaman sınırını aştı; son iyi veri gösteriliyor."
            )
        elif refresh_state.result is not None:
            refresh = refresh_state.result

            kap_snapshot_found = any(
                item.canonical_fund_id == f"fund:tefas:{selected}"
                for item in portfolio_store.list_snapshots()
            )

            if refresh.attempted and refresh.refreshed:
                st.caption(
                    "Otomatik g\u00fcncelleme tamamland\u0131 \u00b7 "
                    f"TEFAS detay={'\u2713' if refresh.detail_written else '-'} \u00b7 "
                    f"fiyat ge\u00e7mi\u015fi={'\u2713' if refresh.history_written else '-'} \u00b7 "
                    f"KAP kontrol={'\u2713' if refresh.portfolio_checked else '-'} \u00b7 "
                    f"KAP snapshot={'\u2713' if kap_snapshot_found else '-'} \u00b7 "
                    f"FDO={'\u2713' if refresh.fdo_checked else '-'}"
                )
            if refresh.warnings and hasattr(st, "warning"):
                st.warning(
                    "Baz\u0131 otomatik kaynaklar izole edildi: "
                    + " | ".join(refresh.warnings[:4])
                )

    try:
        profile = build_fund_profile_read_model(
            selected,
            observation_store=fund_observation_store(),
            portfolio_store=portfolio_store,
        )
    except Exception as exc:
        st.error(f"Fon profili read model üretilemedi: {exc}")
        return selected

    cols = st.columns(5)
    cols[0].metric("Fon", profile.fund_code)
    cols[1].metric("Fiyat", _profile_number(profile.unit_price, digits=6))
    cols[2].metric("Günlük", _profile_percent(profile.daily_return))
    cols[3].metric(
        "Fon toplam değeri",
        "-" if profile.fund_size is None else f"{float(profile.fund_size):,.0f} TL",
    )
    cols[4].metric(
        "Yatırımcı",
        "-" if profile.investor_count is None else f"{profile.investor_count:,}",
    )

    return_cols = st.columns(6)
    for column, horizon in zip(return_cols, ("1H", "1A", "3A", "6A", "YTD", "1Y")):
        column.metric(horizon, _profile_percent(profile.returns.get(horizon)))

    if profile.observation_date is not None:
        st.caption(
            f"TEFAS son gözlem: {profile.observation_date.isoformat()} · "
            f"kayıtlı fiyat gözlemi: {profile.observation_count}"
        )

    if hasattr(st, "line_chart") and profile.price_history:
        st.markdown("#### Fiyat & Büyüklük Geçmişi")
        st.line_chart(
            [{"Tarih": day.isoformat(), "Fiyat": float(value)} for day, value in profile.price_history],
            x="Tarih",
            y="Fiyat",
        )
        if profile.fund_size_history:
            st.line_chart(
                [{"Tarih": day.isoformat(), "Fon Toplam Değeri": float(value)} for day, value in profile.fund_size_history],
                x="Tarih",
                y="Fon Toplam Değeri",
            )
        if profile.investor_history:
            st.line_chart(
                [{"Tarih": day.isoformat(), "Yatırımcı": value} for day, value in profile.investor_history],
                x="Tarih",
                y="Yatırımcı",
            )

    if profile.latest_portfolio is None:
        st.info("Bu fon için henüz KAP portföy snapshot'ı yok.")
    else:
        latest = profile.latest_portfolio
        st.markdown("#### Güncel Portföy")
        st.caption(
            f"Portföy tarihi {latest.portfolio_date.isoformat()} · "
            f"yayın {latest.publication_date.isoformat()} · provider {latest.provider}"
        )
        rows = current_portfolio_rows(latest)
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)

        comparable = sorted(
            (
                item for item in portfolio_store.list_snapshots()
                if item.canonical_fund_id == selected and item.provider == latest.provider
            ),
            key=lambda item: (item.portfolio_date, item.publication_date, item.ingested_at),
        )
        if len(comparable) >= 2:
            change_set = compare_portfolio_snapshots(comparable[-2], comparable[-1])
            st.markdown("#### Son Portföy Değişimi")
            counts = {
                kind: sum(1 for item in change_set.changes if item.kind == kind)
                for kind in PositionChangeKind
            }
            change_cols = st.columns(5)
            change_cols[0].metric("Yeni giriş", counts[PositionChangeKind.NEW_ENTRY])
            change_cols[1].metric("Artırılan", counts[PositionChangeKind.INCREASED])
            change_cols[2].metric("Azaltılan", counts[PositionChangeKind.REDUCED])
            change_cols[3].metric("Tam çıkış", counts[PositionChangeKind.FULL_EXIT])
            change_cols[4].metric("Belirsiz", counts[PositionChangeKind.UNKNOWN])
            change_rows = portfolio_change_rows(change_set)
            if change_rows:
                st.dataframe(change_rows, width="stretch", hide_index=True)

    st.markdown("#### Veri Tazeliği")
    freshness_cols = st.columns(3)
    freshness_cols[0].metric(
        "TEFAS",
        "-" if profile.observation_date is None else profile.observation_date.isoformat(),
    )
    freshness_cols[1].metric(
        "KAP Portföy",
        "-" if profile.latest_portfolio is None else profile.latest_portfolio.portfolio_date.isoformat(),
    )
    freshness_cols[2].metric("Otomatik yenileme", "6 saat")

    return selected

def _render_portfolio_tracking(
    st: Any,
    store: FundPortfolioSnapshotJsonStore,
    pressure_profiles: Mapping[str, StockFundPressureProfile],
    pressure_inputs: Mapping[str, StockFundPressureInput],
    *,
    fund_codes: Iterable[str] = (),
) -> None:
    known_codes = {
        str(code or "").strip().upper()
        for code in fund_codes
        if str(code or "").strip()
    }
    try:
        for snapshot in store.list_snapshots():
            if snapshot.canonical_fund_id.startswith("fund:tefas:"):
                known_codes.add(snapshot.canonical_fund_id.rsplit(":", 1)[-1].strip().upper())
    except PortfolioSnapshotStoreError:
        pass

    if hasattr(st, "button"):
        st.markdown("#### Otomatik KAP Portföy Güncelleme")
        st.caption(
            "Fon Analiz Merkezi açılışta ağ çağrısı yapmaz. Bu düğme, bilinen fon kodları için "
            "resmî KAP bildirim listesini tarar; Portföy Dağılım Raporu bildirimini, ekini ve "
            "snapshot içe aktarımını otomatik yürütür. Manuel PDF yalnız fallback olarak kalır."
        )
        if known_codes:
            st.caption(f"Otomatik tarama evreni: {len(known_codes)} fon kodu.")
        else:
            st.caption("Otomatik tarama için önce TEFAS fon evreni veya kayıtlı bir fon snapshot'ı gerekir.")

        if st.button(
            "Yeni KAP Portföy Raporlarını Otomatik Tara",
            key="fund_portfolio_kap_auto_ingest_button",
            disabled=not known_codes,
        ):
            try:
                summary = auto_ingest_kap_portfolio_reports(
                    store=store,
                    fund_codes=tuple(sorted(known_codes)),
                    network_enabled=True,
                )
            except (KapFundPortfolioError, PortfolioSnapshotStoreError, ValueError) as exc:
                st.error(f"Otomatik KAP portföy güncellemesi çalışmadı: {exc}")
            else:
                if hasattr(st, "success"):
                    st.success(
                        "Otomatik KAP taraması tamamlandı · "
                        f"bulunan={summary.discovered} · "
                        f"yeni={summary.inserted} · "
                        f"zaten kayıtlı={summary.unchanged} · "
                        f"hata={len(summary.failures)}."
                    )
                if summary.failures and hasattr(st, "warning"):
                    preview = " | ".join(
                        f"{item.notification_id}: {item.error}"
                        for item in summary.failures[:5]
                    )
                    st.warning(f"İçe alınamayan KAP bildirimleri: {preview}")

    if hasattr(st, "text_input") and hasattr(st, "button"):
        st.markdown("#### KAP Portföy Raporu İçeri Aktar")
        st.caption(
            "Tekil resmî KAP Portföy Dağılım Raporu bildirim URL\'siyle manuel tetikleme yoludur. "
            "Ağ çağrısı yalnız bu düğmeye açıkça basıldığında yapılır."
        )
        kap_url = st.text_input(
            "KAP bildirim URL\'si",
            key="fund_portfolio_kap_detail_url",
            placeholder="https://www.kap.org.tr/tr/Bildirim/1234567",
        )
        if st.button(
            "KAP Portföy Snapshot\'ını İçeri Aktar",
            key="fund_portfolio_kap_ingest_button",
            disabled=not str(kap_url or "").strip(),
        ):
            try:
                ingestion = ingest_kap_portfolio_report_url(
                    str(kap_url).strip(),
                    store=store,
                    network_enabled=True,
                )
            except (KapFundPortfolioError, PortfolioSnapshotStoreError, ValueError) as exc:
                st.error(f"KAP fon portföyü içeri alınamadı: {exc}")
            else:
                status = "eklendi" if ingestion.store_result.inserted else "zaten kayıtlı"
                if hasattr(st, "success"):
                    st.success(
                        f"{ingestion.snapshot.canonical_fund_id} · "
                        f"{ingestion.snapshot.portfolio_date.isoformat()} snapshot {status}."
                    )

    if (
        hasattr(st, "file_uploader")
        and hasattr(st, "number_input")
        and hasattr(st, "date_input")
        and hasattr(st, "text_input")
        and hasattr(st, "button")
    ):
        st.markdown("##### Alternatif: KAP Portföy PDF Dosyası Yükle")
        st.caption(
            "Gerçek 'Portföy Dağılım Raporu' PDF eki gerekir. KAP bildirim sayfasının "
            "PDF çıktısı veya ekran görüntüsü portföy tablosu içermediği için yeterli değildir. "
            "Rapor dönemi ve KAP yayın tarihi kullanıcı tarafından açıkça doğrulanır."
        )
        uploaded_pdf = st.file_uploader(
            "Portföy dağılım PDF'si",
            type=["pdf"],
            key="fund_portfolio_kap_manual_pdf",
        )
        current_year = date.today().year
        report_year = int(st.number_input(
            "Rapor yılı",
            min_value=2000,
            max_value=2100,
            value=current_year,
            step=1,
            key="fund_portfolio_kap_manual_year",
        ))
        report_month = int(st.number_input(
            "Rapor ayı",
            min_value=1,
            max_value=12,
            value=max(1, date.today().month - 1),
            step=1,
            key="fund_portfolio_kap_manual_month",
        ))
        publication_date = st.date_input(
            "KAP yayın tarihi",
            value=date.today(),
            key="fund_portfolio_kap_manual_publication_date",
        )
        notification_id = st.text_input(
            "KAP bildirim numarası (opsiyonel)",
            key="fund_portfolio_kap_manual_notification_id",
            placeholder="1646130",
        )
        source_reference = st.text_input(
            "Kaynak referansı (opsiyonel)",
            key="fund_portfolio_kap_manual_source_reference",
            placeholder="KAP/Fintables/kurucu site URL veya kısa kaynak notu",
        )
        if st.button(
            "PDF'den Portföy Snapshot'ını İçeri Aktar",
            key="fund_portfolio_kap_manual_ingest_button",
            disabled=uploaded_pdf is None,
        ):
            try:
                ingestion = ingest_kap_portfolio_pdf_upload(
                    uploaded_pdf.getvalue(),
                    filename=getattr(uploaded_pdf, "name", "portfolio.pdf"),
                    report_year=report_year,
                    report_month=report_month,
                    publication_date=publication_date,
                    notification_id=str(notification_id or "").strip() or None,
                    source_reference=str(source_reference or "").strip() or None,
                    store=store,
                )
            except (KapFundPortfolioError, PortfolioSnapshotStoreError, ValueError) as exc:
                st.error(f"KAP PDF portföyü içeri alınamadı: {exc}")
            else:
                status = "eklendi" if ingestion.store_result.inserted else "zaten kayıtlı"
                if hasattr(st, "success"):
                    st.success(
                        f"{ingestion.snapshot.canonical_fund_id} · "
                        f"{ingestion.snapshot.portfolio_date.isoformat()} snapshot {status}. "
                        "İçe aktarım modu: MANUAL_PDF."
                    )

    try:
        model = build_fund_portfolio_tracking_read_model(store)
    except PortfolioSnapshotStoreError:
        st.error("Fon portföy snapshot deposu okunamadı; mevcut fon analiz sonuçları korunuyor.")
        return

    st.divider()
    st.subheader("Fon Portföy Takibi & Baskı Riski")
    st.caption(
        "Tarihli snapshot karşılaştırmasıdır. Ağırlık değişimi tek başına doğrulanmış alım/satım sayılmaz; "
        "bu ekran otomatik AL/SAT üretmez."
    )

    if not model.latest_by_fund:
        st.info("Henüz tarihli fon portföy snapshot verisi yok.")
    else:
        fund_ids = tuple(sorted(model.latest_by_fund))
        label_to_fund_id = {
            (
                fund_id.rsplit(":", 1)[-1].strip()
                if fund_id.startswith("fund:tefas:")
                else fund_id
            ): fund_id
            for fund_id in fund_ids
        }
        selected_fund_label = st.selectbox(
            "Fon portföyü",
            options=tuple(label_to_fund_id),
            index=0,
            key="fund_portfolio_tracking_selected_fund_v2",
        )
        selected_fund = label_to_fund_id[selected_fund_label]
        latest = model.latest_by_fund[selected_fund]
        columns = st.columns(5)
        columns[0].metric("Portföy tarihi", latest.portfolio_date.isoformat())
        columns[1].metric("Yayın tarihi", latest.publication_date.isoformat())
        columns[2].metric("Yayın gecikmesi", f"{(latest.publication_date - latest.portfolio_date).days} gün")
        columns[3].metric("Provider", latest.provider)
        columns[4].metric("Veri kalitesi", latest.data_quality_state.value)
        if latest.source_reference:
            st.caption(f"Kaynak: {latest.source_reference}")

        st.markdown("#### Güncel Portföy")
        current_rows = current_portfolio_rows(latest)
        if current_rows:
            st.dataframe(current_rows, width="stretch", hide_index=True)
        else:
            st.info("Bu snapshot içinde gösterilecek hisse pozisyonu yok.")

        st.markdown("#### Portföy Değişimleri")
        change_set = model.changes_by_fund.get(selected_fund)
        if change_set is None:
            st.info("Değişim karşılaştırması için aynı provider'dan en az iki snapshot gerekir.")
        else:
            change_counts = {kind: sum(item.kind is kind for item in change_set.changes) for kind in PositionChangeKind}
            summary_columns = st.columns(5)
            summary_columns[0].metric("Yeni giriş", change_counts[PositionChangeKind.NEW_ENTRY])
            summary_columns[1].metric("Artırılan", change_counts[PositionChangeKind.INCREASED])
            summary_columns[2].metric("Azaltılan", change_counts[PositionChangeKind.REDUCED])
            summary_columns[3].metric("Tam çıkış", change_counts[PositionChangeKind.FULL_EXIT])
            summary_columns[4].metric("Belirsiz", change_counts[PositionChangeKind.UNKNOWN])
            all_rows = portfolio_change_rows(change_set)
            selected_states = st.multiselect(
                "Değişim türü",
                options=("Yeni giriş", "Artırıldı", "Azaltıldı", "Tam çıkış", "Değişmedi", "Belirsiz"),
                default=("Yeni giriş", "Artırıldı", "Azaltıldı", "Tam çıkış", "Belirsiz"),
                key="fund_portfolio_change_filter",
            )
            filtered = [row for row in all_rows if row["Durum"] in selected_states]
            if filtered:
                st.dataframe(filtered, width="stretch", hide_index=True)
            else:
                st.info("Seçili değişim türlerinde kayıt yok.")

        st.markdown("#### Hisse Bazlı Fon Hareketleri")
        activity_rows = stock_fund_activity_rows(model.stock_activity)
        if activity_rows:
            st.dataframe(activity_rows, width="stretch", hide_index=True)
        else:
            st.info("Hisse bazlı birikim/dağıtım için karşılaştırılabilir snapshot henüz yok.")

    st.markdown("#### Fon/FDO & Baskı Riski")
    if hasattr(st, "button"):
        held_symbols = tuple(sorted({
            position.symbol
            for snapshot in model.latest_by_fund.values()
            for position in snapshot.positions
            if position.asset_type == "EQUITY"
        }))
        st.caption(
            "Tam production güncellemesi yalnız açık düğme isteğiyle çalışır: "
            "portföydeki hisselerin KAP şirket sayfalarından fiili dolaşım tutarını "
            "canonical store'a alır, ardından piyasa likiditesi ve üç gözlemsel baskı skorunu yeniler. "
            "KAP/MKK dışı FDO tahmin edilmez."
        )
        if len(held_symbols) > MAX_FDO_SYMBOLS_PER_REFRESH:
            st.warning(
                f"Bu çalıştırmada en fazla {MAX_FDO_SYMBOLS_PER_REFRESH} hisse FDO'su güncellenebilir; "
                f"mevcut portföy evreni {len(held_symbols)} hisse."
            )
        production_symbols = held_symbols[:MAX_FDO_SYMBOLS_PER_REFRESH]
        if st.button(
            "KAP FDO + Baskı Riskini Tam Güncelle",
            key="fund_pressure_full_production_refresh_button",
            disabled=not bool(production_symbols),
        ):
            try:
                with st.spinner("KAP fiili dolaşım ve piyasa baskı verileri güncelleniyor..."):
                    fdo_summary = populate_kap_free_float_for_symbols(
                        store=default_free_float_store(),
                        symbols=production_symbols,
                        network_enabled=True,
                    )
                    pressure_model = build_fund_pressure_read_model(store)
            except (
                KapFreeFloatError,
                FreeFloatSourceError,
                PortfolioSnapshotStoreError,
                ValueError,
            ) as exc:
                st.error(f"Fon baskı riski production güncellemesi tamamlanamadı: {exc}")
            else:
                live_profiles = dict(pressure_model.profiles)
                live_inputs = dict(pressure_model.inputs)
                if hasattr(st, "session_state"):
                    st.session_state["fund_pressure_profiles"] = live_profiles
                    st.session_state["fund_pressure_inputs"] = live_inputs
                st.success(
                    "Production baskı verisi güncellendi: "
                    f"KAP FDO {fdo_summary.inserted} yeni/değişen, "
                    f"{fdo_summary.unchanged} aynı; "
                    f"{len(live_inputs)} hisse read model; "
                    f"FDO durumu {pressure_model.free_float_source_state}."
                )
                if fdo_summary.failures and hasattr(st, "warning"):
                    st.warning(
                        "KAP FDO alınamayan hisseler izole edildi: "
                        + " | ".join(
                            f"{item.symbol}:{item.error}"
                            for item in fdo_summary.failures[:5]
                        )
                    )
                if pressure_model.warnings and hasattr(st, "warning"):
                    st.warning(
                        "Read model uyarıları: "
                        + " | ".join(pressure_model.warnings[:5])
                    )

    if hasattr(st, "file_uploader"):
        st.caption(
            "Canonical FDO kaynağı KAP/MKK olarak işaretlenmiş, tarihli ve kaynak referanslı "
            "CSV/JSON kaydıdır. Eksik veya bayat FDO tahmin edilmez."
        )
        fdo_file = st.file_uploader(
            "Canonical FDO verisi (CSV/JSON)",
            type=("csv", "json"),
            key="fund_free_float_canonical_file",
        )
        if fdo_file is not None and st.button(
            "Canonical FDO Kaynağını İçeri Aktar",
            key="fund_free_float_canonical_import_button",
        ):
            try:
                records = free_float_records_from_bytes(
                    fdo_file.getvalue(),
                    suffix=Path(fdo_file.name).suffix.lower(),
                )
                result = default_free_float_store().upsert(records)
            except (FreeFloatSourceError, ValueError, TypeError, UnicodeError) as exc:
                st.error(f"Canonical FDO verisi içeri alınamadı: {exc}")
            else:
                st.success(
                    f"Canonical FDO kaynağı güncellendi: {result.inserted} yeni/değişen, "
                    f"{result.unchanged} aynı kayıt."
                )
    live_profiles = dict(pressure_profiles)
    live_inputs = dict(pressure_inputs)
    if hasattr(st, "button"):
        st.caption(
            "Piyasa fiyat/hacim verisi yalnız bu düğmeyle açıkça güncellenir. "
            "Fon pozisyonları mevcut append-only KAP snapshot deposundan okunur. "
            "Canonical KAP/MKK fiili dolaşım kaynağı bulunmadığında Fon/FDO tahmin edilmez."
        )
        if st.button(
            "Baskı Riski Verisini Güncelle",
            key="fund_pressure_read_model_refresh_button",
            disabled=not bool(model.latest_by_fund),
        ):
            try:
                pressure_model = build_fund_pressure_read_model(store)
            except (PortfolioSnapshotStoreError, ValueError) as exc:
                st.error(f"Fon baskı riski read model üretilemedi: {exc}")
            else:
                live_profiles = dict(pressure_model.profiles)
                live_inputs = dict(pressure_model.inputs)
                if hasattr(st, "session_state"):
                    st.session_state["fund_pressure_profiles"] = live_profiles
                    st.session_state["fund_pressure_inputs"] = live_inputs
                if hasattr(st, "success"):
                    st.success(
                        f"Baskı riski read model güncellendi: {len(live_inputs)} hisse. "
                        f"FDO kaynağı: {pressure_model.free_float_source_state}."
                    )
                if pressure_model.warnings and hasattr(st, "warning"):
                    st.warning(
                        "Piyasa verisi alınamayan hisseler izole edildi: "
                        + " | ".join(pressure_model.warnings[:5])
                    )

    if hasattr(st, "session_state"):
        live_profiles = dict(st.session_state.get("fund_pressure_profiles", live_profiles))
        live_inputs = dict(st.session_state.get("fund_pressure_inputs", live_inputs))

    risk_rows = fund_pressure_rows(live_profiles, live_inputs)
    if risk_rows:
        st.dataframe(risk_rows, width="stretch", hide_index=True)
    else:
        st.info(
            "Baskı riski read model henüz güncellenmedi. "
            "Fon/FDO yalnız doğrulanmış fiili dolaşım verisi bağlandığında gösterilir."
        )



def _render_fdo_pressure_production(
    st: Any,
    *,
    portfolio_store: FundPortfolioSnapshotJsonStore,
) -> None:
    """Explicit, bounded KAP FDO refresh + observational pressure read model."""
    st.markdown("### Fon/FDO & Baskı Riski")
    st.caption(
        "KAP/MKK canonical fiili dolaşım verisi ile fon portföy snapshot'larını "
        "birleştirir. Tahmini FDO üretmez; otomatik AL/SAT yetkisi yoktur."
    )

    try:
        snapshots = portfolio_store.list_snapshots()
    except PortfolioSnapshotStoreError as exc:
        st.warning(f"Fon portföy deposu okunamadı: {exc}")
        return

    equity_symbols = sorted({
        position.symbol.strip().upper().removesuffix(".IS")
        for snapshot in snapshots
        for position in snapshot.positions
        if position.asset_type == "EQUITY" and position.symbol.strip()
    })

    if not equity_symbols:
        st.info("Baskı riski için önce en az bir KAP fon portföy snapshot'ı gerekiyor.")
        return

    bounded_symbols = tuple(equity_symbols[:MAX_FDO_SYMBOLS_PER_REFRESH])
    if len(equity_symbols) > len(bounded_symbols):
        st.caption(f"Bounded FDO yenilemesi: {len(bounded_symbols)}/{len(equity_symbols)} hisse işlenecek.")

    refresh_clicked = False
    if hasattr(st, "button"):
        refresh_clicked = st.button(
            "KAP FDO + Baskı Riskini Tam Güncelle",
            key="fund_fdo_pressure_full_refresh_button",
        )

    if refresh_clicked:
        with st.spinner("KAP FDO ve baskı riski güncelleniyor..."):
            try:
                summary = populate_kap_free_float_for_symbols(
                    store=default_free_float_store(),
                    symbols=bounded_symbols,
                    network_enabled=True,
                )
            except KapFreeFloatError as exc:
                st.error(f"KAP FDO güncellenemedi: {exc}")
            else:
                failures = tuple(getattr(summary, "failures", ()) or ())
                st.success("KAP FDO güncellendi: "
                           f"istenen={getattr(summary, 'requested', len(bounded_symbols))}, "
                           f"bulunan={getattr(summary, 'discovered', 0)}, "
                           f"eklenen={getattr(summary, 'inserted', 0)}, "
                           f"değişmeyen={getattr(summary, 'unchanged', 0)}.")
                if failures:
                    st.caption("FDO uyarıları: " + "; ".join(
                        f"{getattr(item, 'symbol', '?')}:{getattr(item, 'error', '?')}"
                        for item in failures[:10]
                    ))

            try:
                pressure_model = build_fund_pressure_read_model(
                    portfolio_store,
                    free_float_store=default_free_float_store(),
                )
            except Exception as exc:
                st.error(f"Baskı riski read model üretilemedi: {exc}")
            else:
                if hasattr(st, "session_state"):
                    st.session_state["fund_pressure_profiles"] = dict(pressure_model.profiles)
                    st.session_state["fund_pressure_inputs"] = dict(pressure_model.inputs)
                    st.session_state["fund_pressure_free_float_source_state"] = pressure_model.free_float_source_state
                    st.session_state["fund_pressure_warnings"] = tuple(pressure_model.warnings)

    profiles = {}
    inputs = {}
    source_state = "UNAVAILABLE"
    warnings = ()
    if hasattr(st, "session_state"):
        profiles = dict(st.session_state.get("fund_pressure_profiles", {}))
        inputs = dict(st.session_state.get("fund_pressure_inputs", {}))
        source_state = str(st.session_state.get("fund_pressure_free_float_source_state", "UNAVAILABLE"))
        warnings = tuple(st.session_state.get("fund_pressure_warnings", ()))

    # Canonical hydration: production stores are authoritative before this
    # browser session presses any refresh button. No network call occurs here.
    if not profiles or source_state == "UNAVAILABLE":
        try:
            hydrated_pressure_model = build_fund_pressure_read_model(
                portfolio_store,
                free_float_store=default_free_float_store(),
            )
        except Exception as exc:
            if hasattr(st, "caption"):
                st.caption(f"Canonical baskı riski read model'i yüklenemedi: {exc}")
        else:
            profiles = dict(hydrated_pressure_model.profiles)
            inputs = dict(hydrated_pressure_model.inputs)
            source_state = hydrated_pressure_model.free_float_source_state
            warnings = tuple(hydrated_pressure_model.warnings)
            if hasattr(st, "session_state"):
                st.session_state["fund_pressure_profiles"] = profiles
                st.session_state["fund_pressure_inputs"] = inputs
                st.session_state["fund_pressure_free_float_source_state"] = source_state
                st.session_state["fund_pressure_warnings"] = warnings

    st.caption(f"Canonical FDO durumu: {source_state}")
    if profiles and len(profiles) < 30:
        st.caption(
            "Fon yoğunluğu / çıkış zorluğu / aktif satış baskısı skorları için "
            "production minimum evreni 30 geçerli hissedir; mevcut evren daha küçükse "
            "skorlar boş kalır ve yapay skor üretilmez."
        )
    if warnings:
        st.caption("Read model uyarıları: " + " | ".join(str(item) for item in warnings[:10]))

    rows = fund_pressure_rows(profiles, inputs)
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)

        zero_like_symbols = []
        for symbol, raw_input in sorted(inputs.items()):
            ratio = raw_input.ownership.fund_free_float_ratio
            normal_days = raw_input.liquidity.liquidation_days_normal
            if (
                ratio == Decimal("0")
                and normal_days == Decimal("0")
                and raw_input.ownership.free_float_shares not in (None, Decimal("0"))
            ):
                zero_like_symbols.append(symbol)

        if zero_like_symbols:
            st.warning(
                "Pressure read model üretildi ancak bazı hisselerde Fon/FDO ve likidasyon 0 görünüyor. "
                "Bu, canonical FDO verisinin mevcut olduğu halde fon portföy snapshotlarında "
                "shares_held / market_value kanıtının eksik veya 0 gelmesine işaret eder. "
                "Semboller: " + ", ".join(zero_like_symbols[:10])
            )
    else:
        st.info("Baskı riski read model henüz güncellenmedi. "
                "Yukarıdaki düğme doğrulanmış KAP FDO verisini çekip read model'i üretir.")

def _render_erste_hungary_evidence_surface(st: Any) -> None:
    st.subheader("Erste Hungary - F1-F4 Evidence")
    try:
        evidence = load_erste_hungary_evidence_surface()
    except FileNotFoundError:
        st.info(
            "Erste Hungary F1-F4 evidence artifacti bulunamadi; "
            "surface guvenli sekilde kullanilamiyor."
        )
        return
    except Exception as exc:
        st.info(f"Erste Hungary evidence surface okunamadi: {exc}")
        return

    counts = {
        key: sum(row.classification == key for row in evidence)
        for key in "ABCDX"
    }
    st.caption(
        "929 canonical fon - "
        + " / ".join(f"{key}={counts[key]}" for key in "ABCDX")
        + " - F5: SAFE_UNAVAILABLE - AL/SAT authority: NONE"
    )
    st.caption(
        "Evidence artifact as_of: "
        + erste_hungary_evidence_as_of(evidence)
        + " - provenance: read-only"
    )

    selected = st.multiselect(
        "Erste Hungary evidence sinifi",
        options=tuple("ABCDX"),
        default=tuple("ABCDX"),
        key="erste_hungary_evidence_class_filter",
    )
    rows = [
        row
        for row in erste_hungary_evidence_rows(evidence)
        if row["Sinif"] in selected
    ]
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("Secilen evidence siniflarinda sonuc yok.")

def render_fund_analysis_center(
    st: Any,
    results: Iterable[FundAnalysisResult] = (),
    *,
    portfolio_store: FundPortfolioSnapshotJsonStore | None = None,
    pressure_profiles: Mapping[str, StockFundPressureProfile] | None = None,
    pressure_inputs: Mapping[str, StockFundPressureInput] | None = None,
    fund_metadata: Mapping[str, Mapping[str, str]] | None = None,
) -> None:
    items = tuple(results)
    st.subheader("Fon Analiz Merkezi")
    st.caption("TEFAS/fon araştırma dikeyidir. BIST taraması çalıştırmaz; otomatik AL/SAT üretmez.")
    counts = {key: sum(item.classification.value == key for item in items) for key in "ABCDX"}
    for column, key in zip(st.columns(5), "ABCDX"):
        column.metric(key, counts[key])
    selected = st.multiselect(
        "Fon s\u0131n\u0131f\u0131",
        options=tuple("ABCDX"),
        default=tuple("ABCDX"),
        key="fund_analysis_class_filter",
    )
    all_rows = list(fund_analysis_rows(items, fund_metadata))
    category_options = tuple(sorted({str(row["Kategori"]) for row in all_rows}))
    selected_categories = st.multiselect(
        "Fon t\u00fcr\u00fc / kategori",
        options=category_options,
        default=category_options,
        key="fund_analysis_category_filter",
    )
    rows = [
        row
        for row in all_rows
        if row["S\u0131n\u0131f"] in selected and row["Kategori"] in selected_categories
    ]
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("Henüz gösterilecek canonical fon analiz sonucu yok.")
    st.caption("Forward takip: 1H / 1A / 3A · outcome tuning kapalı · AL/SAT authority: NONE")

    _render_erste_hungary_evidence_surface(st)

    if portfolio_store is not None or pressure_profiles:
        effective_portfolio_store = (
            portfolio_store if portfolio_store is not None else _EmptyPortfolioStore()
        )
        known_fund_ids = {
            item.canonical_fund_id
            for item in items
            if item.canonical_fund_id.startswith("fund:tefas:")
        }
        try:
            known_fund_ids.update(
                snapshot.canonical_fund_id
                for snapshot in effective_portfolio_store.list_snapshots()
                if snapshot.canonical_fund_id.startswith("fund:tefas:")
            )
        except PortfolioSnapshotStoreError:
            pass

        live_fund_ids = tuple(sorted(
            item.canonical_fund_id
            for item in items
            if item.canonical_fund_id.startswith("fund:tefas:")
        ))
        metadata_fund_ids = tuple(
            fund_id
            for fund_id in live_fund_ids
            if fund_metadata and fund_id in fund_metadata
        )
        profile_fund_ids = (
            metadata_fund_ids
            if metadata_fund_ids
            else live_fund_ids
            if live_fund_ids
            else tuple(sorted(known_fund_ids))
        )

        _render_fdo_pressure_production(
            st,
            portfolio_store=effective_portfolio_store,
        )
        _render_selected_fund_profile(
            st,
            fund_ids=profile_fund_ids,
            portfolio_store=effective_portfolio_store,
            fund_metadata=fund_metadata,
        )


        known_fund_codes = tuple(
            sorted(fund_id.rsplit(":", 1)[-1] for fund_id in known_fund_ids)
        )
        _render_portfolio_tracking(
            st,
            effective_portfolio_store,
            pressure_profiles or {},
            pressure_inputs or {},
            fund_codes=known_fund_codes,
        )


class _EmptyPortfolioStore(FundPortfolioSnapshotJsonStore):
    def __init__(self) -> None:
        pass

    def list_snapshots(self) -> tuple[FundPortfolioSnapshot, ...]:
        return ()
