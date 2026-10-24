from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

import backend.dashboard as desktop


MOBILE_MODULES = (
    "Ana Özet",
    "5'li Hisse",
    "Tarama Sonuçları",
    "Erken Görünürlük",
    "Fon Analiz Merkezi",
    "Sistem Durumu",
)

MOBILE_VIEW_KEYS = {
    "ozet": "Ana Özet",
    "5li": "5'li Hisse",
    "tarama": "Tarama Sonuçları",
    "erken": "Erken Görünürlük",
    "fon": "Fon Analiz Merkezi",
    "sistem": "Sistem Durumu",
}
MOBILE_SECTION_KEYS = {value: key for key, value in MOBILE_VIEW_KEYS.items()}


def _mobile_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 760px;
            padding-top: 0.8rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            padding-bottom: 4rem;
        }
        [data-testid="stHeader"] { background: rgba(0,0,0,0); }
        [data-testid="stStatusWidget"] { display: none !important; }
        [data-testid="stMetric"] {
            border: 1px solid rgba(49, 51, 63, 0.16);
            border-radius: 0.8rem;
            padding: 0.65rem 0.7rem;
            min-height: 5rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.15rem;
            white-space: normal !important;
            overflow-wrap: anywhere;
        }
        div[data-testid="stDataFrame"] { font-size: 0.84rem; }
        button[kind="secondary"], button[kind="primary"] {
            min-height: 3rem;
            border-radius: 0.85rem;
            font-weight: 650;
        }
        .mobile-title {
            font-size: 1.45rem;
            font-weight: 760;
            line-height: 1.15;
            margin: 0.1rem 0 0.15rem 0;
        }
        .mobile-subtitle {
            opacity: 0.72;
            font-size: 0.84rem;
            margin-bottom: 0.35rem;
        }
        .mobile-nav-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.42rem;
            margin: 0.30rem 0 0.45rem 0;
        }
        .mobile-nav-grid a {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 3.15rem;
            padding: 0.52rem 0.45rem;
            border: 1px solid rgba(49, 51, 63, 0.18);
            border-radius: 0.78rem;
            text-decoration: none !important;
            color: inherit !important;
            background: rgba(255, 255, 255, 0.02);
            font-weight: 650;
            line-height: 1.1;
            text-align: center;
        }
        .mobile-nav-grid a.active {
            background: #ff4b4b;
            border-color: #ff4b4b;
            color: white !important;
        }
        .mobile-open-section {
            opacity: 0.68;
            font-size: 0.80rem;
            margin: 0.10rem 0 0.25rem 0;
        }
        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMarkdownContainer"] .mobile-open-section) {
            margin-bottom: -0.35rem;
        }
        @media (max-width: 600px) {
            .block-container { padding-left: 0.5rem; padding-right: 0.5rem; padding-top: 0.45rem; }
            h1 { font-size: 1.55rem !important; }
            h2 { font-size: 1.28rem !important; }
            h3 { font-size: 1.12rem !important; }
            [data-testid="column"] { min-width: 0 !important; }
            [data-testid="stMetric"] { min-height: 4.5rem; }
            div[data-testid="stDataFrame"] { font-size: 0.78rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _initial_section() -> str:
    try:
        view = st.query_params.get("view")
    except Exception:
        view = None
    if isinstance(view, list):
        view = view[0] if view else None
    if view in MOBILE_VIEW_KEYS:
        return MOBILE_VIEW_KEYS[view]
    current = st.session_state.get("mobile_section")
    if current in MOBILE_MODULES:
        return current
    return MOBILE_MODULES[0]


def _set_section(section: str) -> None:
    st.session_state["mobile_section"] = section
    try:
        st.query_params["view"] = MOBILE_SECTION_KEYS[section]
    except Exception:
        pass


def _mobile_nav() -> str:
    selected = _initial_section()
    items = (
        ("🏠 Özet", "Ana Özet"),
        ("⭐ 5'li", "5'li Hisse"),
        ("🔎 Tarama", "Tarama Sonuçları"),
        ("👁 Erken", "Erken Görünürlük"),
        ("💼 Fon", "Fon Analiz Merkezi"),
        ("⚙ Sistem", "Sistem Durumu"),
    )
    links = []
    for label, section in items:
        key = MOBILE_SECTION_KEYS[section]
        active = " active" if selected == section else ""
        links.append(
            f'<a class="mobile-nav-item{active}" href="?view={key}" target="_self">{label}</a>'
        )
    st.markdown(
        '<div class="mobile-nav-grid">' + "".join(links) + "</div>",
        unsafe_allow_html=True,
    )
    return selected



def _render_fund_center() -> None:
    from backend.app.funds.portfolio_tracking import fund_portfolio_snapshot_store
    from backend.app.funds.ui_live_refresh import refresh_fund_analysis_if_requested
    from backend.app.funds.canonical_result_store import (
        FundCanonicalResultStoreError,
        load_last_good_fund_analysis_results,
        save_last_good_fund_analysis_results,
    )
    from backend.app.funds.tefas_universe_nonblocking_refresh import queue_tefas_universe_refresh
    from backend.app.funds.live_pipeline import get_last_live_fund_metadata
    from backend.app.funds.fund_profile import build_fund_profile_read_model
    from backend.app.funds.store import fund_observation_store

    live_results_key = "fund_analysis_live_results"
    current_live_results = tuple(st.session_state.get(live_results_key, ()))
    if not current_live_results:
        try:
            rehydrated_results = load_last_good_fund_analysis_results()
        except FundCanonicalResultStoreError:
            rehydrated_results = ()
        if rehydrated_results:
            current_live_results = rehydrated_results
            st.session_state[live_results_key] = rehydrated_results

    metadata = get_last_live_fund_metadata()
    st.markdown("### Fon Analiz Merkezi")
    st.caption("TEFAS/fon araştırma görünümü · otomatik AL/SAT yetkisi yoktur.")

    refresh_requested = st.button(
        "TEFAS verisini şimdi güncelle",
        key="mobile_fund_refresh",
        width="stretch",
        type="primary",
    )
    refresh_outcome = refresh_fund_analysis_if_requested(
        requested=False,
        current_results=current_live_results,
    )

    now_utc = datetime.now(timezone.utc)
    last_attempt = st.session_state.get("fund_analysis_auto_refresh_attempt_at")
    auto_due = not current_live_results
    if isinstance(last_attempt, datetime) and last_attempt.tzinfo is not None:
        auto_due = auto_due or (now_utc - last_attempt >= timedelta(hours=6))

    if auto_due and not refresh_requested:
        refresh_state = queue_tefas_universe_refresh(
            loader=lambda: refresh_fund_analysis_if_requested(
                requested=True,
                current_results=current_live_results,
            ),
            timeout_seconds=20.0,
        )
        if refresh_state.status in ("STARTED", "RUNNING"):
            st.session_state["fund_analysis_auto_refresh_attempt_at"] = now_utc
            st.caption("TEFAS arka planda güncelleniyor; son iyi veri gösteriliyor.")
        elif refresh_state.status == "DONE" and refresh_state.result is not None:
            refresh_outcome = refresh_state.result
            if refresh_outcome.refreshed:
                save_last_good_fund_analysis_results(refresh_outcome.results)
                st.session_state[live_results_key] = refresh_outcome.results
                current_live_results = refresh_outcome.results
                metadata = get_last_live_fund_metadata()
        elif refresh_state.status in ("FAILED", "TIMEOUT"):
            st.caption("Otomatik yenileme izole edildi; son iyi veri korunuyor.")

    if refresh_requested:
        st.session_state["fund_analysis_auto_refresh_attempt_at"] = now_utc
        with st.spinner("TEFAS canlı fon verisi güncelleniyor..."):
            refresh_outcome = refresh_fund_analysis_if_requested(
                requested=True,
                current_results=current_live_results,
            )
        if refresh_outcome.error_message:
            st.error("TEFAS güncellenemedi; son iyi veri korunuyor.")
            st.caption(refresh_outcome.error_message)
        elif refresh_outcome.refreshed:
            save_last_good_fund_analysis_results(refresh_outcome.results)
            st.session_state[live_results_key] = refresh_outcome.results
            current_live_results = refresh_outcome.results
            metadata = get_last_live_fund_metadata()
            st.success(f"Güncellendi · {len(current_live_results)} fon")

    items = tuple(current_live_results)
    counts = {key: sum(item.classification.value == key for item in items) for key in "ABCDX"}

    # Veri sağlığı: canonical sonuç varlığı ile kanıt kapsamasını birbirinden ayır.
    # X oranı çok yüksekse "Hazır" demek yanıltıcı olur; motor kuralı/fill değiştirilmez.
    unavailable_counts = {family: 0 for family in ("F1", "F2", "F3", "F4", "F5")}
    reason_counts: dict[str, int] = {}
    for item in items:
        for family in item.unavailable_families:
            if family in unavailable_counts:
                unavailable_counts[family] += 1
        reason_counts[item.eligibility_reason] = reason_counts.get(item.eligibility_reason, 0) + 1

    x_ratio = (counts["X"] / len(items)) if items else 0.0
    if not items:
        data_status = "Bekleniyor"
    elif x_ratio >= 0.80:
        data_status = "Kısmi · kanıt açığı"
    elif x_ratio >= 0.35:
        data_status = "Kısmi"
    else:
        data_status = "Hazır"

    c1, c2 = st.columns(2)
    c1.metric("Fon sayısı", len(items))
    c2.metric("Veri durumu", data_status)

    if items:
        non_x = len(items) - counts["X"]
        st.caption(
            f"Sınıflandırılabilir kapsam: {non_x}/{len(items)} (%{(non_x / len(items) * 100):.1f}) · "
            "NO FORCED FILL: eksik kanıt X olarak korunur."
        )

        with st.expander("Veri sağlığı / neden X?", expanded=(x_ratio >= 0.80)):
            try:
                records = tuple(fund_observation_store().list_records())
            except Exception:
                records = ()

            fund_price_counts: dict[str, int] = {}
            fund_flow_counts: dict[str, int] = {}
            for raw in records:
                if raw.get("record_type") != "FundDailyObservation" or raw.get("provider") != "TEFAS":
                    continue
                fund_id = str(raw.get("canonical_fund_id") or "").strip()
                if not fund_id:
                    continue
                if raw.get("unit_price") not in (None, ""):
                    fund_price_counts[fund_id] = fund_price_counts.get(fund_id, 0) + 1
                if raw.get("fund_size") not in (None, "") and raw.get("investor_count") not in (None, ""):
                    fund_flow_counts[fund_id] = fund_flow_counts.get(fund_id, 0) + 1

            history_funds = sum(value >= 3 for value in fund_price_counts.values())
            flow_funds = sum(value >= 2 for value in fund_flow_counts.values())

            h1, h2 = st.columns(2)
            h1.metric("F3 geçmiş kapsamı", f"{history_funds}/{len(items)}")
            h2.metric("F4 akış kapsamı", f"{flow_funds}/{len(items)}")

            family_names = {
                "F1": "Kategori içi göreli sıralama",
                "F2": "TEFAS getiri/trend",
                "F3": "Risk / oynaklık-geçmiş",
                "F4": "Fon büyüklüğü-yatırımcı akışı",
                "F5": "Maliyet / rejim / dağılım",
            }
            health_rows = []
            for family in ("F1", "F2", "F3", "F4", "F5"):
                missing = unavailable_counts[family]
                available = len(items) - missing
                health_rows.append({
                    "Kanıt": family,
                    "Alan": family_names[family],
                    "Mevcut": available,
                    "Eksik": missing,
                    "Kapsama %": round((available / len(items) * 100), 1) if items else 0.0,
                })
            st.dataframe(pd.DataFrame(health_rows), width="stretch", hide_index=True)

            reason_rows = [
                {"Neden": reason, "Fon": count}
                for reason, count in sorted(reason_counts.items(), key=lambda kv: (-kv[1], kv[0]))
            ]
            if reason_rows:
                st.caption("Sınıflandırma nedenleri")
                st.dataframe(pd.DataFrame(reason_rows), width="stretch", hide_index=True)

            if x_ratio >= 0.80:
                st.warning(
                    "Canonical sonuç seti mevcut, ancak bağımsız kanıt ailesi kapsamı yetersiz. "
                    "Bu ekran sınıfları yapay olarak doldurmaz; veri katmanı tamamlanana kadar X oranı yüksek kalabilir."
                )

    class_labels = {
        "A": "A · Güçlü / Öncelikli",
        "B": "B · Gelişen",
        "C": "C · İzle",
        "D": "D · Zayıflayan",
        "X": "X · Uygun değil / eksik veri",
    }
    class_cols = st.columns(2)
    for idx, key in enumerate("ABCDX"):
        with class_cols[idx % 2]:
            st.metric(class_labels[key], counts[key])

    if not items:
        st.info("Henüz gösterilecek canonical fon analiz sonucu yok.")
        st.caption("TEFAS güncellemesini çalıştırabilir veya son iyi verinin oluşmasını bekleyebilirsiniz.")
        return

    def _label(item):
        meta = metadata.get(item.canonical_fund_id, {}) if metadata else {}
        code = str(meta.get("fund_code") or item.canonical_fund_id.rsplit(":", 1)[-1]).strip()
        name = str(meta.get("fund_name") or "").strip()
        return f"{code} - {name}" if name else code

    ranking = {"A": 0, "B": 1, "C": 2, "D": 3, "X": 4}
    sorted_items = sorted(
        items,
        key=lambda item: (
            ranking.get(item.classification.value, 9),
            -len(item.positive_families),
            item.canonical_fund_id,
        ),
    )

    st.markdown("#### Öne çıkan fonlar")
    top_rows = []
    for item in sorted_items[:8]:
        meta = metadata.get(item.canonical_fund_id, {}) if metadata else {}
        top_rows.append({
            "Fon": _label(item),
            "Sınıf": item.classification.value,
            "Durum": item.class_label,
            "Kategori": str(meta.get("category_name") or item.category_id or "-"),
            "Pozitif": len(item.positive_families),
            "Dikkat": len(item.caution_families),
        })
    st.dataframe(pd.DataFrame(top_rows), width="stretch", hide_index=True)

    labels = {_label(item): item for item in sorted_items}
    selected_label = st.selectbox(
        "Fon detayı",
        options=tuple(labels),
        key="mobile_fund_selected",
    )
    selected_item = labels[selected_label]
    meta = metadata.get(selected_item.canonical_fund_id, {}) if metadata else {}

    d1, d2 = st.columns(2)
    d1.metric("Sınıf", selected_item.classification.value)
    d2.metric("Durum", selected_item.class_label)
    st.caption(
        f"Kategori: {str(meta.get('category_name') or selected_item.category_id or '-')} · "
        f"Gerekçe: {selected_item.eligibility_reason}"
    )

    family_rows = [
        {"Kanıt": "Pozitif", "Aileler": ", ".join(selected_item.positive_families) or "-"},
        {"Kanıt": "Nötr", "Aileler": ", ".join(selected_item.neutral_families) or "-"},
        {"Kanıt": "Dikkat", "Aileler": ", ".join(selected_item.caution_families) or "-"},
        {"Kanıt": "Eksik", "Aileler": ", ".join(selected_item.unavailable_families) or "-"},
    ]
    st.dataframe(pd.DataFrame(family_rows), width="stretch", hide_index=True)

    try:
        profile = build_fund_profile_read_model(
            selected_item.canonical_fund_id,
            observation_store=fund_observation_store(),
            portfolio_store=fund_portfolio_snapshot_store(),
        )
    except Exception:
        profile = None

    if profile is not None:
        st.markdown("#### Performans ve profil")
        p1, p2 = st.columns(2)
        p1.metric(
            "Fiyat",
            "-" if profile.unit_price is None else f"{float(profile.unit_price):,.6f}",
        )
        p2.metric(
            "Fon büyüklüğü",
            "-" if profile.fund_size is None else f"{float(profile.fund_size):,.0f} TL",
        )

        horizons = ("1A", "3A", "6A", "1Y")
        hcols = st.columns(2)
        for idx, horizon in enumerate(horizons):
            value = profile.returns.get(horizon)
            display = "-" if value is None else f"{float(value) * 100:.2f}%"
            hcols[idx % 2].metric(horizon, display)

        if profile.investor_count is not None:
            st.metric("Yatırımcı", f"{profile.investor_count:,}")
        if profile.observation_date is not None:
            st.caption(f"TEFAS son gözlem: {profile.observation_date.isoformat()}")

        if profile.latest_portfolio is not None:
            st.markdown("#### Son KAP portföyü")
            st.caption(
                f"Portföy tarihi: {profile.latest_portfolio.portfolio_date.isoformat()}"
            )
            positions = sorted(
                profile.latest_portfolio.positions,
                key=lambda x: (
                    x.portfolio_weight is None,
                    -(x.portfolio_weight or 0),
                    x.symbol,
                ),
            )[:10]
            rows = []
            for pos in positions:
                weight = "-"
                if pos.portfolio_weight is not None:
                    weight = f"{float(pos.portfolio_weight) * 100:.2f}%"
                rows.append({
                    "Varlık": pos.symbol,
                    "Tür": pos.asset_type,
                    "Portföy %": weight,
                })
            if rows:
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.caption("Forward takip: 1H / 1A / 3A · outcome tuning kapalı · AL/SAT authority: NONE")

def _render_system_status() -> None:
    from backend.app.diagnostics.system_check import sistem_kontrolu_calistir

    st.subheader("Sistem Durumu")
    st.caption("Ağ kullanmadan çalışma ortamını ve ana Hisse Robotu zincirlerini doğrular.")

    run_now = st.button("Sistem kontrolünü çalıştır", width="stretch", type="primary")
    report = st.session_state.get("mobile_system_check_report")
    if run_now:
        with st.spinner("Sistem kontrolü çalışıyor..."):
            report = sistem_kontrolu_calistir(
                proje_koku=Path(__file__).resolve().parents[1]
            )
        st.session_state["mobile_system_check_report"] = report

    if report is None:
        st.info("Kontrolü başlatmak için düğmeye dokunun.")
        return

    cols = st.columns(3)
    cols[0].metric("Başarılı", report.basarili_sayisi)
    cols[1].metric("Uyarı", report.uyari_sayisi)
    cols[2].metric("Hata", report.basarisiz_sayisi)

    if report.kullanima_hazir:
        st.success("Sistem kullanıma hazır.")
    else:
        st.error("Kritik kontrol hatası var.")

    rows = [
        {
            "Kontrol": item.ad,
            "Durum": item.durum,
            "Açıklama": item.aciklama,
        }
        for item in report.kontroller
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def main() -> None:
    st.set_page_config(
        page_title="Hisse Robotu Mobil",
        page_icon="📱",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    desktop.arayuz_stili_uygula()
    _mobile_css()

    st.markdown('<div class="mobile-title">📱 Hisse Robotu Mobil</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="mobile-subtitle">Kişisel kullanım · mevcut Hisse Robotu motoru · mobil görünüm</div>',
        unsafe_allow_html=True,
    )

    selected = _mobile_nav()
    st.markdown(
        f'<div class="mobile-open-section">Açık bölüm: {selected}</div>',
        unsafe_allow_html=True,
    )

    if selected == "Ana Özet":
        st.subheader("Ana Özet")
        desktop.gunluk_operasyon_paneli_formu()
    elif selected == "5'li Hisse":
        st.subheader("Bugünün 5 Adayı")
        st.caption(
            "Mevcut günlük operasyon motorundaki 5 aday ve karar bağlamı gösterilir; "
            "masaüstü karar sözleşmesi değiştirilmez."
        )
        desktop.gunluk_operasyon_paneli_formu()
    elif selected == "Tarama Sonuçları":
        st.subheader("BIST Tarama Sonuçları")
        desktop.bist_toplu_tarama_formu()
    elif selected == "Erken Görünürlük":
        st.subheader("Erken Görünürlük")
        st.caption(
            "Research sıralama hareketi/erken görünürlük mevcut BIST toplu tarama ekranından okunur; "
            "AL/SAT kararı üretmez."
        )
        desktop.bist_toplu_tarama_formu()
    elif selected == "Fon Analiz Merkezi":
        _render_fund_center()
    else:
        _render_system_status()


if __name__ == "__main__":
    main()
