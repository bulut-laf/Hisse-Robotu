from __future__ import annotations

import os
from pathlib import Path
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from backend.app.analysis.fundamental_analysis import (
    build_fundamental_snapshot,
)
from backend.app.analysis.fundamental_quality import (
    apply_optional_fundamental_filter,
    calculate_fundamental_quality,
)
from backend.app.data.fundamental_score_store import (
    FundamentalScoreJsonStore,
    FundamentalScoreStoreError,
)
from backend.app.analysis.fundamental_score_history import (
    comparison_rows,
    history_rows,
    latest_score_change,
)
from backend.app.analysis.sector_reference import (
    SectorReferenceError,
    build_company_ratio_references,
    compare_company_to_sector,
    references_from_csv_bytes,
    sector_comparison_rows,
)
from backend.app.analysis.sector_score_ranking import (
    SectorScoreRankingError,
    build_sector_score_ranking,
    sector_score_ranking_rows,
)
from backend.app.data.fundamental_data import (
    FundamentalDataError,
    evaluate_fundamental_freshness,
    periods_from_csv_bytes,
    periods_from_json_bytes,
)
from backend.app.data.kap_api_config import (
    load_kap_api_configuration,
    validate_kap_api_configuration,
)

from backend.app.backtest.backtest_service import BacktestServiceError
from backend.app.backtest.same_data_comparison import (
    BAZ_ANALIZ,
    KARSILASTIRMA_ANALIZI,
    SameDataComparisonError,
    SameDataComparisonMetric,
    SameDataComparisonResult,
    SameDataComparisonService,
)
from backend.app.history.backtest_history import (
    GUNCEL_TEKNIK_ANALIZ,
    PORTFOY_ANALIZI,
    TEK_HISSE_ANALIZI,
    BacktestHistoryError,
    BacktestHistoryRecord,
    BacktestHistoryStore,
)
from backend.app.history.backtest_history_comparison import (
    ESIT,
    ILK_KAYIT,
    IKINCI_KAYIT,
    BacktestHistoryComparisonError,
    HistoryComparisonMetric,
    gecmis_kayitlarini_karsilastir,
)
from backend.app.history.backtest_history_filter import (
    BacktestHistoryFilter,
    gecmis_kayitlarini_filtrele,
    kayit_sembolleri,
    kayit_tarih_araligi,
)
from backend.app.history.backtest_history_pagination import (
    SIRALAMA_DUSUS_ARTAN,
    SIRALAMA_EN_ESKI,
    SIRALAMA_EN_YENI,
    SIRALAMA_GETIRI_AZALAN,
    SIRALAMA_SEMBOL_ARTAN,
    gecmis_kayitlarini_sayfala,
    gecmis_kayitlarini_sirala,
)
from backend.app.history.backtest_history_summary import (
    gecmis_ozeti_hesapla,
    gecmis_performans_noktalari,
)
from backend.app.history.backtest_history_backup import (
    BacktestHistoryBackupError,
    BacktestHistoryBackupService,
)
from backend.app.ui.backtest_dashboard import (
    BacktestDashboardService,
    DashboardBacktestRequest,
    DashboardResult,
)
from backend.app.ui.comparison_table import (
    ComparisonDisplayRow,
    compact_comparison_records,
    comparison_leader_records,
    comparison_table_html,
)
from backend.app.ui.portfolio_dashboard import (
    PortfolioDashboardError,
    PortfolioDashboardRequest,
    PortfolioDashboardResult,
    PortfolioDashboardService,
    ozsermaye_eksen_araligi,
)
from backend.app.ui.report_export import (
    ReportExportError,
    portfoy_dosya_adlari,
    portfoy_katki_csv_baytlari,
    portfoy_ozsermaye_csv_baytlari,
    portfoy_pdf_baytlari,
    tek_hisse_dosya_adlari,
    tek_hisse_islem_csv_baytlari,
    tek_hisse_pdf_baytlari,
)
from backend.app.data.data_freshness import BatchDataFreshnessResult, DataFreshnessResult
from backend.app.ui.current_session_snapshot import (
    CurrentSessionSnapshotError,
    guncel_seans_ozeti_getir,
)
from backend.app.ui.market_regime_dashboard import (
    MarketRegimeContext,
    MarketRegimeDashboardError,
    MarketRegimeDashboardService,
    piyasa_rejimi_baglami_olustur,
)
from backend.app.ui.live_analysis_dashboard import (
    LiveAnalysisDashboardError,
    LiveAnalysisDashboardService,
    LiveAnalysisRequest,
    LiveAnalysisResult,
    OpenPositionDashboardRequest,
    OpenPositionDashboardService,
)
from backend.app.analysis.position_monitor import PositionMonitoringResult
from backend.app.analysis.market_scanner import (
    EVREN_OZEL_LISTE,
    TARAMA_EVRENLERI,
    BistMarketScannerService,
    MarketScanRequest,
    MarketScanResult,
    MarketScannerError,
    aday_tablosu_kayitlari,
    ozel_sembol_metinini_ayristir,
)
from backend.app.compliance.dashboard_manual_vbts import (
    DashboardManualVbtsError,
    load_dashboard_vbts_dataset,
)
from backend.app.compliance.dashboard_market_scanner_source_factory import (
    DashboardMarketScannerSourceError,
    build_dashboard_market_scanner,
)
from backend.app.compliance.dashboard_vbts_manager import (
    DashboardVbtsManagerError,
    add_vbts_record,
    audit_events_csv_bytes,
    audit_display_rows,
    build_vbts_record,
    classify_vbts_records,
    configured_vbts_csv_path,
    delete_vbts_record,
    inspect_vbts_backup,
    list_vbts_backups,
    list_vbts_records,
    prune_vbts_backups,
    purge_expired_vbts_records,
    read_audit_events,
    read_operational_status,
    restore_vbts_backup,
    synchronize_vbts_operational_state,
    sync_active_vbts_csv,
    validate_vbts_system_health,
)
from backend.app.compliance.kap_factory import build_kap_vbts_service
from backend.app.analysis.trend_scan_policy import (
    REJIM_POZITIF,
    REJIM_RISKLI,
    REJIM_SECICI,
    rejime_gore_trend_politikasi,
)
from backend.app.analysis.momentum_discovery import (
    SINIF_DIRENCE_YAKLASIYOR,
    SINIF_ERKEN_UYARI,
    SINIF_HACIM_BIRIKIMI,
    SINIF_KALICI_HAZIRLIK,
    SINIF_SIKISMA,
    MomentumCandidate,
    MomentumDiscoveryError,
    MomentumDiscoveryRequest,
    MomentumDiscoveryResult,
    MomentumDiscoveryService,
    momentum_aday_tablosu,
)
from backend.app.analysis.momentum_walk_forward import (
    MomentumWalkForwardError,
    MomentumWalkForwardRequest,
    MomentumWalkForwardResult,
    MomentumWalkForwardService,
    sinyal_gecmisi_tablosu,
    walk_forward_izleme_disi_tablosu,
    walk_forward_tablosu,
)
from backend.app.analysis.loss_analysis import (
    LossAnalysisResult,
    analyze_trade_losses,
    cause_table,
    diagnostic_table,
    journal_table,
)
from backend.app.history.trade_journal import (
    DENEME_HESABI,
    GERCEK_HESAP,
    HESAP_TURLERI,
    TradeJournalError,
    TradeJournalStore,
    TradeRecord,
    csv_template_bytes,
    records_from_csv_bytes,
    records_to_csv_bytes,
)
from backend.app.risk.safety_lock import (
    SafetyDecision,
    SafetyPolicy,
    TradeProposal,
    evaluate_trade_safety,
)


GORUNUM_SECENEKLERI = {
    "Pozitif + Nötr": "pozitif-notr",
    "Yalnızca Pozitif": "pozitif",
    "Yalnızca Nötr": "notr",
    "Tümü": "tum",
}

ANALIZ_MODLARI = (
    "Tek Hisse",
    "Güncel Teknik Analiz",
    "Temel Analiz",
    "Piyasa Rejimi",
    "Momentum Keşif",
    "BIST Toplu Tarama",
    "Açık Pozisyon İzleme",
    "İşlem Kayıp Analizi",
    "Aynı Veri Karşılaştırması",
    "Çoklu Hisse Portföyü",
    "Analiz Geçmişi",
)

TARAMA_PROFILLERI = {
    "Gevşek": "gevsek",
    "Dengeli": "dengeli",
    "Sıkı": "siki",
}


def yuzde_yaz(deger: float) -> str:
    return f"%{deger:,.2f}"


def para_yaz(deger: float) -> str:
    return f"{deger:,.2f}"


def tarih_saat_yaz(deger: object) -> str:
    """Tarihleri gereksiz gece yarısı bilgisi olmadan gösterir."""

    if hasattr(deger, "to_pydatetime"):
        deger = deger.to_pydatetime()

    if isinstance(deger, datetime):
        if deger.time() == datetime.min.time():
            return deger.strftime("%Y-%m-%d")
        return deger.strftime("%Y-%m-%d %H:%M")

    if isinstance(deger, date):
        return deger.strftime("%Y-%m-%d")

    metin = str(deger)
    if metin.endswith(" 00:00:00"):
        return metin.removesuffix(" 00:00:00")
    return metin


def arayuz_stili_uygula() -> None:
    """Metrikleri ve tabloları dar ekranlarda daha okunabilir tutar."""

    st.markdown(
        """
        <style>
        [data-testid="stMetric"] {
            border: 1px solid rgba(49, 51, 63, 0.16);
            border-radius: 0.75rem;
            padding: 0.75rem 0.85rem;
            min-height: 6.1rem;
        }
        [data-testid="stMetricValue"] {
            font-size: clamp(1.25rem, 2.2vw, 2.05rem);
            line-height: 1.18;
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
            overflow-wrap: anywhere;
            word-break: normal;
        }
        [data-testid="stMetricLabel"] {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid rgba(49, 51, 63, 0.12);
            border-radius: 0.65rem;
        }
        @media (max-width: 900px) {
            [data-testid="stMetric"] {
                min-height: 5.4rem;
                padding: 0.6rem 0.7rem;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.25rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metrik_izgarasi_goster(
    metrikler: tuple[tuple[str, str], ...],
) -> None:
    """Metrikleri iki sütunlu, taşma yapmayan satırlara böler."""

    for baslangic in range(0, len(metrikler), 2):
        sutunlar = st.columns(2)
        for sutun, (etiket, deger) in zip(
            sutunlar,
            metrikler[baslangic : baslangic + 2],
        ):
            sutun.metric(etiket, deger)

def responsive_karsilastirma_goster(
    rows: tuple[ComparisonDisplayRow, ...],
) -> None:
    """Karşılaştırmayı dar ekran ve yazdırma görünümünde taşmadan gösterir."""

    records = compact_comparison_records(rows)
    if not records:
        st.info("Karşılaştırılacak ölçüt bulunamadı.")
        return

    st.markdown(
        comparison_table_html(rows),
        unsafe_allow_html=True,
    )

    leaders = comparison_leader_records(rows)
    if leaders:
        with st.expander("Ölçüt liderleri", expanded=False):
            st.dataframe(
                pd.DataFrame(leaders),
                width="stretch",
                hide_index=True,
                column_config={
                    "Ölçüt": st.column_config.TextColumn(width="medium"),
                    "Lider": st.column_config.TextColumn(width="medium"),
                },
            )


def indirme_dugmeleri_goster(
    indirmeler: tuple[tuple[str, bytes, str, str], ...],
) -> None:
    """İndirme düğmelerini iki sütunlu, dar ekran dostu düzende gösterir."""

    for baslangic in range(0, len(indirmeler), 2):
        sutunlar = st.columns(2)
        for sutun, (etiket, veri, dosya_adi, mime) in zip(
            sutunlar,
            indirmeler[baslangic : baslangic + 2],
        ):
            sutun.download_button(
                etiket,
                data=veri,
                file_name=dosya_adi,
                mime=mime,
                width="stretch",
                key=f"indir_{dosya_adi}",
            )


def tek_hisse_disari_aktarim_goster(sonuc: DashboardResult) -> None:
    """Tek-hisse sonucu için CSV ve PDF indirme seçeneklerini gösterir."""

    adlar = tek_hisse_dosya_adlari(sonuc)
    indirmeler: list[tuple[str, bytes, str, str]] = [
        (
            "İşlemleri CSV indir",
            tek_hisse_islem_csv_baytlari(sonuc),
            adlar.csv,
            "text/csv; charset=utf-8",
        )
    ]
    try:
        indirmeler.append(
            (
                "PDF raporunu indir",
                tek_hisse_pdf_baytlari(sonuc),
                adlar.pdf,
                "application/pdf",
            )
        )
    except ReportExportError as hata:
        st.warning(str(hata))

    st.subheader("Raporu dışa aktar")
    indirme_dugmeleri_goster(tuple(indirmeler))


def portfoy_disari_aktarim_goster(
    sonuc: PortfolioDashboardResult,
) -> None:
    """Portföy sonucu için CSV ve PDF indirme seçeneklerini gösterir."""

    adlar = portfoy_dosya_adlari(sonuc)
    indirmeler: list[tuple[str, bytes, str, str]] = [
        (
            "Hisse katkısını CSV indir",
            portfoy_katki_csv_baytlari(sonuc),
            adlar.contribution_csv,
            "text/csv; charset=utf-8",
        ),
        (
            "Günlük özsermayeyi CSV indir",
            portfoy_ozsermaye_csv_baytlari(sonuc),
            adlar.equity_csv,
            "text/csv; charset=utf-8",
        ),
    ]
    try:
        indirmeler.insert(
            0,
            (
                "PDF raporunu indir",
                portfoy_pdf_baytlari(sonuc),
                adlar.pdf,
                "application/pdf",
            ),
        )
    except ReportExportError as hata:
        st.warning(str(hata))

    st.subheader("Raporu dışa aktar")
    indirme_dugmeleri_goster(tuple(indirmeler))


def gecmis_zamani_yaz(zaman: str) -> str:
    try:
        deger = datetime.fromisoformat(zaman)
    except ValueError:
        return zaman
    return deger.strftime("%d.%m.%Y %H:%M:%S")


def gecmise_kaydet(
    sonuc: DashboardResult | PortfolioDashboardResult | LiveAnalysisResult,
) -> BacktestHistoryRecord | None:
    """Başarılı sonucu yerel analiz geçmişine kaydeder."""

    depo = BacktestHistoryStore()
    try:
        if isinstance(sonuc, DashboardResult):
            return depo.tek_hisse_kaydet(sonuc)
        if isinstance(sonuc, PortfolioDashboardResult):
            return depo.portfoy_kaydet(sonuc)
        if isinstance(sonuc, LiveAnalysisResult):
            return depo.guncel_analiz_kaydet(sonuc)
        raise TypeError("Desteklenmeyen analiz geçmişi sonucu.")
    except (BacktestHistoryError, OSError, ValueError, TypeError) as hata:
        st.warning(f"Analiz geçmişine kaydedilemedi: {hata}")
        return None


def gecmis_kaydi_etiketi(kayit: BacktestHistoryRecord) -> str:
    tur = {
        TEK_HISSE_ANALIZI: "Tek Hisse",
        PORTFOY_ANALIZI: "Portföy",
        GUNCEL_TEKNIK_ANALIZ: "Güncel Teknik Analiz",
    }.get(kayit.analiz_turu, kayit.analiz_turu)
    semboller = ", ".join(kayit.semboller)
    return (
        f"{gecmis_zamani_yaz(kayit.kaydedilme_zamani)} · "
        f"{tur} · {semboller}"
    )


def karsilastirma_degeri_yaz(
    metrik: HistoryComparisonMetric,
    deger: float,
) -> str:
    if metrik.birim == "para":
        return para_yaz(deger)
    if metrik.birim == "yuzde":
        return yuzde_yaz(deger)
    if metrik.birim == "sayi":
        return f"{deger:,.0f}"
    return f"{deger:,.2f}"


def karsilastirma_farki_yaz(metrik: HistoryComparisonMetric) -> str:
    if metrik.birim == "para":
        return f"{metrik.fark:+,.2f}"
    if metrik.birim == "yuzde":
        return f"{metrik.fark:+,.2f} puan"
    if metrik.birim == "sayi":
        return f"{metrik.fark:+,.0f}"
    return f"{metrik.fark:+,.2f}"


def karsilastirma_lideri_yaz(metrik: HistoryComparisonMetric) -> str:
    if metrik.lider == ILK_KAYIT:
        return "Baz analiz"
    if metrik.lider == IKINCI_KAYIT:
        return "Karşılaştırılan"
    if metrik.lider == ESIT and metrik.iyilik_yonu != "notr":
        return "Eşit"
    return "—"


def analiz_karsilastirmasi_goster(
    depo: BacktestHistoryStore,
    baz_kayit: BacktestHistoryRecord,
    kayitlar: tuple[BacktestHistoryRecord, ...],
) -> None:
    adaylar = tuple(
        kayit
        for kayit in kayitlar
        if kayit.analiz_turu == baz_kayit.analiz_turu
        and kayit.kayit_kimligi != baz_kayit.kayit_kimligi
    )
    st.subheader("Analiz karşılaştırması")
    if not adaylar:
        st.caption(
            "Karşılaştırma için aynı türde en az iki farklı geçmiş kayıt gerekir."
        )
        return

    karsilastirma_acik = st.checkbox(
        "İkinci bir analizle karşılaştır",
        value=False,
        key=f"karsilastirma_acik_{baz_kayit.kayit_kimligi}",
    )
    if not karsilastirma_acik:
        return

    ikinci_kimlik = st.selectbox(
        "Karşılaştırılacak analiz",
        options=tuple(kayit.kayit_kimligi for kayit in adaylar),
        format_func=lambda kimlik: gecmis_kaydi_etiketi(
            next(k for k in adaylar if k.kayit_kimligi == kimlik)
        ),
        key=f"karsilastirma_kaydi_{baz_kayit.kayit_kimligi}",
    )
    ikinci = next(
        kayit for kayit in adaylar if kayit.kayit_kimligi == ikinci_kimlik
    )

    try:
        karsilastirma = gecmis_kayitlarini_karsilastir(
            baz_kayit,
            ikinci,
        )
    except (BacktestHistoryComparisonError, TypeError, ValueError) as hata:
        st.error(str(hata))
        return

    if karsilastirma.dogrudan_karsilastirilabilir:
        if karsilastirma.ayarlar_ayni:
            st.info("Aynı veri ve aynı ayarlarla üretilmiş iki kayıt karşılaştırılıyor.")
        else:
            st.success(
                "Aynı sembol, dönem ve fiyat verisi kullanılmış. "
                "Performans farkı ayar değişikliğini değerlendirmek için uygundur."
            )
    else:
        st.warning(
            "Kayıtlar aynı veri tabanında değil. Farklar yalnızca genel eğilim "
            "olarak yorumlanmalıdır."
        )

    for uyari in karsilastirma.uyarilar:
        st.caption(f"• {uyari}")

    satirlar = tuple(
        ComparisonDisplayRow(
            label=metrik.etiket,
            base_value=karsilastirma_degeri_yaz(
                metrik, metrik.ilk_deger
            ),
            comparison_value=karsilastirma_degeri_yaz(
                metrik, metrik.ikinci_deger
            ),
            difference=karsilastirma_farki_yaz(metrik),
            leader=karsilastirma_lideri_yaz(metrik),
        )
        for metrik in karsilastirma.metrikler
    )
    responsive_karsilastirma_goster(satirlar)

    with st.expander("Karşılaştırma kimlikleri", expanded=False):
        st.write(
            {
                "Baz veri kimliği": baz_kayit.veri_kimligi,
                "Karşılaştırılan veri kimliği": ikinci.veri_kimligi,
                "Baz ayar kimliği": baz_kayit.ayar_kimligi,
                "Karşılaştırılan ayar kimliği": ikinci.ayar_kimligi,
            }
        )


def gecmis_yonetimi_goster(
    depo: BacktestHistoryStore,
    kayitlar: tuple[BacktestHistoryRecord, ...],
    varsayilan_kayit: BacktestHistoryRecord,
) -> None:
    """Seçili geçmiş kayıtları için güvenli ve açık silme akışı gösterir."""

    with st.expander("Geçmiş yönetimi", expanded=False):
        st.warning(
            "Silinen analiz kaydı ve ona ait CSV/PDF dosyaları geri alınamaz. "
            "Proje kaynak dosyaları ve diğer geçmiş kayıtları etkilenmez."
        )
        secili_kimlikler = st.multiselect(
            "Silinecek kayıtlar",
            options=tuple(kayit.kayit_kimligi for kayit in kayitlar),
            default=(varsayilan_kayit.kayit_kimligi,),
            format_func=lambda kimlik: gecmis_kaydi_etiketi(
                next(k for k in kayitlar if k.kayit_kimligi == kimlik)
            ),
            key=f"gecmis_silinecek_{varsayilan_kayit.kayit_kimligi}",
        )
        onay_kutusu = st.checkbox(
            "Seçili kayıtların kalıcı olarak silineceğini anlıyorum.",
            value=False,
            key=f"gecmis_silme_onayi_{varsayilan_kayit.kayit_kimligi}",
        )
        onay_metni = st.text_input(
            "Onaylamak için SİL yazın",
            value="",
            key=f"gecmis_silme_metni_{varsayilan_kayit.kayit_kimligi}",
        )
        silme_hazir = (
            bool(secili_kimlikler)
            and onay_kutusu
            and onay_metni.strip().upper() == "SİL"
        )
        silme_istendi = st.button(
            "Seçili kayıtları kalıcı olarak sil",
            type="primary",
            width="stretch",
            disabled=not silme_hazir,
            key=f"gecmis_sil_{varsayilan_kayit.kayit_kimligi}",
        )
        if not silme_istendi:
            return

        try:
            silinenler = depo.kayitlari_sil(tuple(secili_kimlikler))
        except (BacktestHistoryError, OSError, ValueError, TypeError) as hata:
            st.error(f"Seçili geçmiş kayıtları silinemedi: {hata}")
            return

        st.session_state["gecmis_silme_bildirimi"] = (
            f"{len(silinenler)} analiz kaydı kalıcı olarak silindi."
        )
        st.rerun()


def gecmis_yedekleme_goster(
    depo: BacktestHistoryStore,
    kayitlar: tuple[BacktestHistoryRecord, ...],
) -> None:
    """Analiz geçmişini ZIP olarak yedekler ve güvenle geri yükler."""

    servis = BacktestHistoryBackupService(depo)
    with st.expander("Yedekleme ve geri yükleme", expanded=False):
        st.caption(
            "Yedek yalnızca analiz geçmişi metadata, CSV ve PDF dosyalarını "
            "içerir; proje kaynakları ve piyasa verileri dahil edilmez."
        )
        kimlikten_kayit = {
            kayit.kayit_kimligi: kayit for kayit in kayitlar
        }
        secili_kimlikler = st.multiselect(
            "Yedeklenecek kayıtlar",
            options=tuple(kimlikten_kayit),
            default=tuple(kimlikten_kayit),
            format_func=lambda kimlik: gecmis_kaydi_etiketi(
                kimlikten_kayit[kimlik]
            ),
            key="gecmis_yedeklenecek_kayitlar",
        )
        if secili_kimlikler:
            try:
                yedek = servis.yedek_olustur(tuple(secili_kimlikler))
            except (
                BacktestHistoryBackupError,
                BacktestHistoryError,
                OSError,
                ValueError,
                TypeError,
            ) as hata:
                st.error(f"Analiz geçmişi yedeği oluşturulamadı: {hata}")
            else:
                zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    "Seçili kayıtları ZIP olarak yedekle",
                    data=yedek,
                    file_name=f"hisse_robotu_analiz_gecmisi_{zaman}.zip",
                    mime="application/zip",
                    width="stretch",
                    key="gecmis_yedek_indir",
                )
        else:
            st.info("ZIP yedeği için en az bir kayıt seçin.")

        st.divider()
        st.markdown("**ZIP yedeğini geri yükle**")
        yuklenen = st.file_uploader(
            "Analiz geçmişi ZIP yedeği",
            type=("zip",),
            accept_multiple_files=False,
            key="gecmis_yedek_yukle",
        )
        if yuklenen is None:
            return

        yedek_baytlari = yuklenen.getvalue()
        try:
            onizleme = servis.yedegi_incele(yedek_baytlari)
        except (
            BacktestHistoryBackupError,
            BacktestHistoryError,
            OSError,
            ValueError,
            TypeError,
        ) as hata:
            st.error(f"Analiz geçmişi yedeği doğrulanamadı: {hata}")
            return

        metrik_izgarasi_goster(
            (
                ("Yedekteki kayıt", str(onizleme.toplam_kayit)),
                ("Yeni kayıt", str(onizleme.yeni_kayit)),
                ("Zaten mevcut", str(onizleme.zaten_mevcut)),
                ("Dosya sayısı", str(onizleme.toplam_dosya)),
            )
        )
        if onizleme.yeni_kayit == 0:
            st.info("Yedekteki kayıtların tamamı analiz geçmişinde zaten mevcut.")

        geri_yukleme_onayi = st.checkbox(
            "Yedekteki yeni kayıtların analiz geçmişine eklenmesini onaylıyorum.",
            value=False,
            key="gecmis_geri_yukleme_onayi",
        )
        geri_yukle = st.button(
            "Yedeği geri yükle",
            type="primary",
            width="stretch",
            disabled=(
                not geri_yukleme_onayi or onizleme.yeni_kayit == 0
            ),
            key="gecmis_yedegi_geri_yukle",
        )
        if not geri_yukle:
            return

        try:
            sonuc = servis.yedegi_geri_yukle(yedek_baytlari)
        except (
            BacktestHistoryBackupError,
            BacktestHistoryError,
            OSError,
            ValueError,
            TypeError,
        ) as hata:
            st.error(f"Analiz geçmişi yedeği geri yüklenemedi: {hata}")
            return

        st.session_state["gecmis_geri_yukleme_bildirimi"] = (
            f"{sonuc.geri_yuklenen} analiz kaydı geri yüklendi; "
            f"{sonuc.atlanan_ayni_kayit} aynı kayıt atlandı."
        )
        st.rerun()



def gecmis_performans_ozeti_goster(
    kayitlar: tuple[BacktestHistoryRecord, ...],
) -> None:
    """Filtrelenmiş analiz geçmişinin risk-getiri özetini gösterir."""

    if not kayitlar:
        return

    try:
        ozet = gecmis_ozeti_hesapla(kayitlar)
        noktalar = gecmis_performans_noktalari(kayitlar)
    except (TypeError, ValueError) as hata:
        st.warning(f"Analiz geçmişi özeti hazırlanamadı: {hata}")
        return

    with st.expander("Geçmiş performans özeti", expanded=True):
        metrik_izgarasi_goster(
            (
                ("Filtrelenmiş kayıt", str(ozet.toplam_kayit)),
                ("Benzersiz sembol", str(ozet.benzersiz_sembol_sayisi)),
                ("Toplam işlem", str(ozet.toplam_tamamlanan_islem)),
                (
                    "Medyan getiri",
                    yuzde_yaz(ozet.medyan_getiri_yuzde)
                    if ozet.medyan_getiri_yuzde is not None
                    else "-",
                ),
                (
                    "Medyan maks. düşüş",
                    yuzde_yaz(ozet.medyan_maksimum_dusus_yuzde)
                    if ozet.medyan_maksimum_dusus_yuzde is not None
                    else "-",
                ),
                (
                    "Ort. kâr faktörü",
                    f"{ozet.ortalama_kar_faktoru:.2f}"
                    if ozet.ortalama_kar_faktoru is not None
                    else "-",
                ),
            )
        )

        lider_sutunlari = st.columns(2)
        en_yuksek = ozet.en_yuksek_getiri_kaydi
        en_dusuk = ozet.en_dusuk_dusus_kaydi
        with lider_sutunlari[0]:
            st.markdown("**En yüksek toplam getiri**")
            if en_yuksek is not None:
                st.write(gecmis_kaydi_etiketi(en_yuksek))
                st.caption(yuzde_yaz(en_yuksek.toplam_getiri_yuzde))
        with lider_sutunlari[1]:
            st.markdown("**En düşük maksimum düşüş**")
            if en_dusuk is not None:
                st.write(gecmis_kaydi_etiketi(en_dusuk))
                st.caption(yuzde_yaz(en_dusuk.maksimum_dusus_yuzde))

        if len(noktalar) >= 2:
            grafik_verisi = pd.DataFrame(
                [
                    {
                        "Analiz": nokta.etiket,
                        "Analiz türü": nokta.analiz_turu,
                        "Maksimum düşüş (%)": nokta.maksimum_dusus_yuzde,
                        "Toplam getiri (%)": nokta.toplam_getiri_yuzde,
                        "Tamamlanan işlem": nokta.tamamlanan_islem_sayisi,
                    }
                    for nokta in noktalar
                ]
            )
            st.subheader("Risk-getiri görünümü")
            st.scatter_chart(
                grafik_verisi,
                x="Maksimum düşüş (%)",
                y="Toplam getiri (%)",
                color="Analiz türü",
                size="Tamamlanan işlem",
                width="stretch",
                height=360,
            )
        else:
            st.info(
                "Risk-getiri grafiği için en az iki filtrelenmiş kayıt gerekir."
            )

        st.caption(
            "Özet, filtrelenmiş kayıtları betimleyici olarak karşılaştırır; "
            "farklı sembol ve ayarları tek bir birleşik portföy sonucu saymaz."
        )

def _gecmis_alt_sozluk(
    kayit: BacktestHistoryRecord,
    anahtar: str,
) -> dict[str, object]:
    bilgiler = kayit.ozel_bilgiler or {}
    deger = bilgiler.get(anahtar, {})
    return deger if isinstance(deger, dict) else {}


def guncel_analiz_gecmis_kaydi_goster(
    kayit: BacktestHistoryRecord,
) -> None:
    """Kaydedilmiş güncel teknik analiz sonucunu yeniden gösterir."""

    fiyat = _gecmis_alt_sozluk(kayit, "fiyat_verisi")
    teknik = _gecmis_alt_sozluk(kayit, "teknik_teyit")
    plan = _gecmis_alt_sozluk(kayit, "islem_plani")
    pozisyon = _gecmis_alt_sozluk(kayit, "risk_ve_pozisyon")
    kimlikler = _gecmis_alt_sozluk(kayit, "kimlikler")

    st.success(kayit.baslik)
    st.caption(
        f"Kaydedilme: {gecmis_zamani_yaz(kayit.kaydedilme_zamani)} · "
        f"{kayit.donem}"
    )
    metrik_izgarasi_goster(
        (
            ("Fiyat verisi", str(fiyat.get("durum") or "—")),
            ("Fiyat veri tarihi", str(fiyat.get("son_veri_tarihi") or "—")),
            ("Teknik teyit skoru", f"{teknik.get('skor', '—')}/100"),
            ("Teyit durumu", str(teknik.get("durum") or "—")),
            ("İşlem kararı", str(plan.get("karar") or "—")),
            ("Plan tipi", str(plan.get("plan_tipi") or "—")),
        )
    )

    teyit_tab, plan_tab, kimlik_tab = st.tabs(
        ("Teknik teyit özeti", "İşlem planı", "Analiz kimlikleri")
    )
    with teyit_tab:
        metrik_izgarasi_goster(
            (
                ("Haftalık yön", str(teknik.get("haftalik_yon") or "—")),
                ("Haftalık skor", str(teknik.get("haftalik_skor") or "—")),
                ("Günlük yön", str(teknik.get("gunluk_yon") or "—")),
                ("Günlük skor", str(teknik.get("gunluk_skor") or "—")),
                ("Saatlik yön", str(teknik.get("saatlik_yon") or "—")),
                ("Saatlik skor", str(teknik.get("saatlik_skor") or "—")),
            )
        )
        aciklama_listesi_goster(
            "Pozitif teyitler",
            tuple(teknik.get("pozitif_nedenler") or ()),
            "Kaydedilmiş pozitif teyit yok.",
        )
        aciklama_listesi_goster(
            "Riskler",
            tuple(teknik.get("riskler") or ()),
            "Kaydedilmiş risk yok.",
        )

    with plan_tab:
        metrik_izgarasi_goster(
            (
                ("Son kapanış", opsiyonel_fiyat_yaz(plan.get("son_kapanis"))),
                ("ATR14", opsiyonel_fiyat_yaz(plan.get("atr14"))),
                ("İzleme tetik seviyesi", opsiyonel_fiyat_yaz(plan.get("izleme_tetik_fiyati"))),
                ("Referans giriş", opsiyonel_fiyat_yaz(plan.get("referans_giris"))),
                ("Stop-loss", opsiyonel_fiyat_yaz(plan.get("stop_loss"))),
                ("Hedef 1", opsiyonel_fiyat_yaz(plan.get("hedef_1"))),
                ("Hedef 2", opsiyonel_fiyat_yaz(plan.get("hedef_2"))),
                ("Lot sayısı", str(pozisyon.get("lot_sayisi") or "—")),
                ("Risk bütçesi", opsiyonel_fiyat_yaz(pozisyon.get("risk_butcesi"))),
                ("Planlanan risk", opsiyonel_fiyat_yaz(pozisyon.get("planlanan_risk"))),
            )
        )
        aciklama_listesi_goster(
            "Beklenen teyitler",
            tuple(plan.get("beklenen_teyitler") or ()),
            "Kaydedilmiş ek teyit yok.",
        )
        aciklama_listesi_goster(
            "Planı geçersiz kılan koşullar",
            tuple(plan.get("gecersizlik_kosullari") or ()),
            "Kaydedilmiş geçersizlik koşulu yok.",
        )

    with kimlik_tab:
        st.write(
            {
                "Veri kimliği": kimlikler.get("veri_kimligi"),
                "Teknik analiz kimliği": kimlikler.get("teknik_analiz_kimligi"),
                "İşlem planı kimliği": kimlikler.get("islem_plani_kimligi"),
            }
        )


def analiz_gecmisi_goster() -> None:
    """Kalıcı geçmişteki önceki analizleri filtreleyip gösterir."""

    with st.sidebar:
        st.header("Analiz geçmişi")
        tur_etiketi = st.selectbox(
            "Kayıt türü",
            options=("Tümü", "Tek Hisse", "Portföy", "Güncel Teknik Analiz"),
            index=0,
        )
        arama = st.text_input(
            "Geçmişte ara",
            value="",
            placeholder="Sembol, başlık veya kimlik",
        )
        siralama_etiketi = st.selectbox(
            "Sıralama",
            options=(
                "En yeni kayıt",
                "En eski kayıt",
                "Toplam getiri: yüksekten düşüğe",
                "Maksimum düşüş: düşükten yükseğe",
                "Sembol: A-Z",
            ),
            index=0,
        )
        sayfa_boyutu = st.selectbox(
            "Sayfa başına kayıt",
            options=(10, 25, 50, 100),
            index=1,
        )

    silme_bildirimi = st.session_state.pop(
        "gecmis_silme_bildirimi",
        None,
    )
    if silme_bildirimi:
        st.success(silme_bildirimi)

    geri_yukleme_bildirimi = st.session_state.pop(
        "gecmis_geri_yukleme_bildirimi",
        None,
    )
    if geri_yukleme_bildirimi:
        st.success(geri_yukleme_bildirimi)

    tur_esleme = {
        "Tümü": None,
        "Tek Hisse": TEK_HISSE_ANALIZI,
        "Portföy": PORTFOY_ANALIZI,
        "Güncel Teknik Analiz": GUNCEL_TEKNIK_ANALIZ,
    }
    depo = BacktestHistoryStore()
    try:
        tum_kayitlar = depo.kayitlari_listele(
            analiz_turu=tur_esleme[tur_etiketi],
            limit=500,
        )
    except (BacktestHistoryError, ValueError) as hata:
        st.error(str(hata))
        return

    sembol_secenekleri = kayit_sembolleri(tum_kayitlar)
    tarih_araligi = kayit_tarih_araligi(tum_kayitlar)
    with st.sidebar:
        secili_semboller = st.multiselect(
            "Sembol filtresi",
            options=sembol_secenekleri,
            default=(),
            help="Boş bırakıldığında tüm semboller gösterilir.",
        )
        baslangic_tarihi = None
        bitis_tarihi = None
        if tarih_araligi is not None:
            tarih_secimi = st.date_input(
                "Kaydedilme tarihi aralığı",
                value=tarih_araligi,
                min_value=tarih_araligi[0],
                max_value=tarih_araligi[1],
                format="DD.MM.YYYY",
                help="Backtest dönemi değil, kaydın oluşturulduğu tarih kullanılır.",
            )
            if isinstance(tarih_secimi, (tuple, list)):
                if len(tarih_secimi) == 2:
                    baslangic_tarihi, bitis_tarihi = tarih_secimi
                elif len(tarih_secimi) == 1:
                    baslangic_tarihi = bitis_tarihi = tarih_secimi[0]
            else:
                baslangic_tarihi = bitis_tarihi = tarih_secimi

    try:
        filtrelenmis_kayitlar = gecmis_kayitlarini_filtrele(
            tum_kayitlar,
            BacktestHistoryFilter(
                arama=arama,
                semboller=tuple(secili_semboller),
                baslangic_tarihi=baslangic_tarihi,
                bitis_tarihi=bitis_tarihi,
            ),
        )
        siralama_esleme = {
            "En yeni kayıt": SIRALAMA_EN_YENI,
            "En eski kayıt": SIRALAMA_EN_ESKI,
            "Toplam getiri: yüksekten düşüğe": SIRALAMA_GETIRI_AZALAN,
            "Maksimum düşüş: düşükten yükseğe": SIRALAMA_DUSUS_ARTAN,
            "Sembol: A-Z": SIRALAMA_SEMBOL_ARTAN,
        }
        sirali_kayitlar = gecmis_kayitlarini_sirala(
            filtrelenmis_kayitlar,
            siralama_esleme[siralama_etiketi],
        )
    except (TypeError, ValueError) as hata:
        st.error(f"Analiz geçmişi filtrelenemedi: {hata}")
        return

    toplam_sayfa = max(
        1,
        (len(sirali_kayitlar) + int(sayfa_boyutu) - 1)
        // int(sayfa_boyutu),
    )
    with st.sidebar:
        sayfa = st.selectbox(
            "Sayfa",
            options=tuple(range(1, toplam_sayfa + 1)),
            index=0,
            format_func=lambda deger: f"{deger} / {toplam_sayfa}",
        )

    try:
        sayfa_sonucu = gecmis_kayitlarini_sayfala(
            sirali_kayitlar,
            sayfa=int(sayfa),
            sayfa_boyutu=int(sayfa_boyutu),
        )
    except (TypeError, ValueError) as hata:
        st.error(f"Analiz geçmişi sayfalanamadı: {hata}")
        return

    kayitlar = sirali_kayitlar
    sayfa_kayitlari = sayfa_sonucu.kayitlar
    if sayfa_sonucu.toplam_kayit:
        st.caption(
            f"Filtre sonucu: {sayfa_sonucu.toplam_kayit} / "
            f"{len(tum_kayitlar)} kayıt · "
            f"Sayfa {sayfa_sonucu.sayfa} / "
            f"{sayfa_sonucu.toplam_sayfa} · "
            f"{sayfa_sonucu.ilk_sira}–{sayfa_sonucu.son_sira}. kayıtlar"
        )
    else:
        st.caption(
            f"Filtre sonucu: 0 / {len(tum_kayitlar)} kayıt"
        )
    gecmis_yedekleme_goster(depo, kayitlar)

    if not tum_kayitlar:
        st.info(
            "Henüz kayıtlı analiz bulunmuyor. Başarılı backtest ve güncel "
            "teknik analiz sonuçları burada saklanacak."
        )
        st.caption(f"Kayıt klasörü: {depo.kok_klasor}")
        return

    if not sirali_kayitlar:
        st.info(
            "Seçilen arama, sembol ve tarih filtreleriyle eşleşen "
            "analiz kaydı bulunamadı."
        )
        st.caption(f"Kayıt klasörü: {depo.kok_klasor}")
        return

    performans_kayitlari = tuple(
        k for k in sirali_kayitlar
        if k.analiz_turu in (TEK_HISSE_ANALIZI, PORTFOY_ANALIZI)
    )
    gecmis_performans_ozeti_goster(performans_kayitlari)

    secilen_kimlik = st.selectbox(
        "Geçmiş analiz",
        options=tuple(kayit.kayit_kimligi for kayit in sayfa_kayitlari),
        format_func=lambda kimlik: gecmis_kaydi_etiketi(
            next(k for k in sayfa_kayitlari if k.kayit_kimligi == kimlik)
        ),
    )
    kayit = next(
        kayit for kayit in sayfa_kayitlari
        if kayit.kayit_kimligi == secilen_kimlik
    )

    if kayit.analiz_turu == GUNCEL_TEKNIK_ANALIZ:
        guncel_analiz_gecmis_kaydi_goster(kayit)
    else:
        st.success(kayit.baslik)
        st.caption(
            f"Kaydedilme: {gecmis_zamani_yaz(kayit.kaydedilme_zamani)} · "
            f"Dönem: {kayit.donem}"
        )
        metrik_izgarasi_goster(
            (
                ("Bitiş sermayesi", para_yaz(kayit.bitis_sermayesi)),
                ("Toplam getiri", yuzde_yaz(kayit.toplam_getiri_yuzde)),
                ("Maksimum düşüş", yuzde_yaz(kayit.maksimum_dusus_yuzde)),
                ("Tamamlanan işlem", str(kayit.tamamlanan_islem_sayisi)),
                ("Atlanan", str(kayit.atlanan_islem_sayisi)),
                (
                    "Kâr faktörü",
                    f"{kayit.kar_faktoru:.2f}"
                    if kayit.kar_faktoru is not None
                    else "-",
                ),
            )
        )

    gecmis_yonetimi_goster(depo, kayitlar, kayit)

    with st.expander("Kayıt ayrıntıları", expanded=False):
        ayrintilar: dict[str, object] = {
            "Semboller": ", ".join(kayit.semboller),
            "Veri kimliği": kayit.veri_kimligi,
            "Ayar kimliği": kayit.ayar_kimligi,
        }
        if kayit.analiz_turu != GUNCEL_TEKNIK_ANALIZ:
            ayrintilar["Güncel düşüş"] = yuzde_yaz(
                kayit.guncel_dusus_yuzde
            )
        if kayit.analiz_kimligi is not None:
            ayrintilar["Analiz kimliği"] = kayit.analiz_kimligi
        if kayit.kazanma_yuzde is not None:
            ayrintilar["Kazanma oranı"] = yuzde_yaz(
                kayit.kazanma_yuzde
            )
        if kayit.ortalama_sermaye_kullanim_yuzde is not None:
            ayrintilar["Ortalama sermaye kullanımı"] = yuzde_yaz(
                kayit.ortalama_sermaye_kullanim_yuzde
            )
        if kayit.maksimum_pozisyon is not None:
            ayrintilar["Maksimum pozisyon"] = kayit.maksimum_pozisyon
        st.write(ayrintilar)

    if kayit.analiz_turu != GUNCEL_TEKNIK_ANALIZ:
        analiz_karsilastirmasi_goster(depo, kayit, kayitlar)

    indirme_etiketleri = {
        "pdf": "PDF raporunu indir",
        "islemler_csv": "İşlemleri CSV indir",
        "katki_csv": "Hisse katkısını CSV indir",
        "ozsermaye_csv": "Günlük özsermayeyi CSV indir",
        "guncel_analiz_csv": "Güncel analiz özetini CSV indir",
    }
    indirmeler: list[tuple[str, bytes, str, str]] = []
    for dosya in kayit.dosyalar:
        try:
            veri = depo.dosya_baytlari(kayit, dosya.tur)
        except BacktestHistoryError as hata:
            st.warning(str(hata))
            continue
        indirmeler.append(
            (
                indirme_etiketleri.get(dosya.tur, dosya.dosya_adi),
                veri,
                dosya.dosya_adi,
                dosya.mime,
            )
        )

    if indirmeler:
        st.subheader("Kayıtlı raporlar")
        indirme_dugmeleri_goster(tuple(indirmeler))
    st.caption(f"Kayıt klasörü: {depo.kok_klasor}")


def tek_hisse_sonucu_goster(sonuc: DashboardResult) -> None:
    ozet = sonuc.ozet

    st.success(f"{ozet.sembol} backtest’i tamamlandı.")
    st.caption(
        f"Fiyat dönemi: {ozet.fiyat_donemi} · "
        f"{ozet.fiyat_bar_sayisi} bar"
    )

    metrik_izgarasi_goster(
        (
            ("Bitiş sermayesi", para_yaz(ozet.bitis_sermayesi)),
            ("Toplam getiri", yuzde_yaz(ozet.toplam_getiri_yuzde)),
            ("Maksimum düşüş", yuzde_yaz(ozet.maksimum_dusus_yuzde)),
            ("Tamamlanan işlem", str(ozet.tamamlanan_islem_sayisi)),
            ("Kazanma oranı", yuzde_yaz(ozet.kazanma_yuzde)),
            (
                "Kâr faktörü",
                (
                    f"{ozet.kar_faktoru:.2f}"
                    if ozet.kar_faktoru is not None
                    else "-"
                ),
            ),
        )
    )

    with st.expander("Analiz ayrıntıları", expanded=False):
        st.write(
            {
                "Analiz kimliği": ozet.analiz_kimligi,
                "Veri kimliği": ozet.veri_kimligi,
                "Ayar kimliği": ozet.ayar_kimligi,
                "Güncel düşüş": yuzde_yaz(
                    ozet.guncel_dusus_yuzde
                ),
                "Atlanan sinyal": ozet.atlanan_sinyal_sayisi,
                "Hizalanmış Al-Tut getirisi": (
                    yuzde_yaz(ozet.al_tut_getiri_yuzde)
                    if ozet.al_tut_getiri_yuzde is not None
                    else "-"
                ),
            }
        )

    st.subheader("Tamamlanan işlemler")
    kayitlar = sonuc.islem_kayitlari()

    if not kayitlar:
        st.info("Seçilen ayarlarda tamamlanan işlem bulunamadı.")
    else:
        tablo = pd.DataFrame(kayitlar)
        st.dataframe(
            tablo,
            width="stretch",
            hide_index=True,
            column_config={
                "Giriş Fiyatı": st.column_config.NumberColumn(
                    format="%.2f"
                ),
                "Çıkış Fiyatı": st.column_config.NumberColumn(
                    format="%.2f"
                ),
                "Net Getiri (%)": st.column_config.NumberColumn(
                    format="%.2f%%"
                ),
            },
        )

    tek_hisse_disari_aktarim_goster(sonuc)


def portfoy_sonucu_goster(
    sonuc: PortfolioDashboardResult,
) -> None:
    ozet = sonuc.ozet

    st.success(
        f"{len(ozet.semboller)} hisselik portföy backtest’i tamamlandı."
    )
    st.caption(
        f"Portföy dönemi: {ozet.portfoy_donemi} · "
        f"{', '.join(ozet.semboller)}"
    )

    metrik_izgarasi_goster(
        (
            ("Bitiş sermayesi", para_yaz(ozet.bitis_sermayesi)),
            ("Toplam getiri", yuzde_yaz(ozet.toplam_getiri_yuzde)),
            ("Maksimum düşüş", yuzde_yaz(ozet.maksimum_dusus_yuzde)),
            (
                "Kâr faktörü",
                f"{ozet.kar_faktoru:.2f}"
                if ozet.kar_faktoru is not None
                else "-",
            ),
            ("Tamamlanan işlem", str(ozet.tamamlanan_islem_sayisi)),
            ("Atlanan işlem", str(ozet.atlanan_islem_sayisi)),
            (
                "Ortalama kullanım",
                yuzde_yaz(ozet.ortalama_sermaye_kullanim_yuzde),
            ),
            (
                "Maksimum pozisyon",
                str(ozet.gerceklesen_maksimum_pozisyon),
            ),
        )
    )

    with st.expander("Portföy ayrıntıları", expanded=False):
        st.write(
            {
                "Ayar kimliği": ozet.ayar_kimligi,
                "Portföy veri kimliği": ozet.portfoy_veri_kimligi,
                "Güncel düşüş": yuzde_yaz(
                    ozet.guncel_dusus_yuzde
                ),
                "Maksimum sermaye kullanımı": yuzde_yaz(
                    ozet.maksimum_sermaye_kullanim_yuzde
                ),
            }
        )

    ozsermaye_kayitlari = sonuc.ozsermaye_kayitlari()
    if ozsermaye_kayitlari:
        st.subheader("Günlük portföy özsermayesi")
        ozsermaye = pd.DataFrame(ozsermaye_kayitlari)
        ozsermaye["Tarih"] = pd.to_datetime(ozsermaye["Tarih"])
        eksen_araligi = ozsermaye_eksen_araligi(ozsermaye_kayitlari)
        grafik_ayari: dict[str, object] = {
            "mark": {"type": "line"},
            "encoding": {
                "x": {
                    "field": "Tarih",
                    "type": "temporal",
                    "title": "Tarih",
                },
                "y": {
                    "field": "Özsermaye",
                    "type": "quantitative",
                    "title": "Özsermaye",
                    "scale": {
                        "zero": False,
                        "domain": list(eksen_araligi)
                        if eksen_araligi is not None
                        else None,
                    },
                },
                "tooltip": [
                    {"field": "Tarih", "type": "temporal", "title": "Tarih"},
                    {
                        "field": "Özsermaye",
                        "type": "quantitative",
                        "title": "Özsermaye",
                        "format": ",.2f",
                    },
                    {
                        "field": "Düşüş (%)",
                        "type": "quantitative",
                        "title": "Düşüş (%)",
                        "format": ".2f",
                    },
                    {
                        "field": "Açık Pozisyon",
                        "type": "quantitative",
                        "title": "Açık Pozisyon",
                    },
                ],
            },
            "height": 340,
        }
        st.vega_lite_chart(
            ozsermaye,
            grafik_ayari,
            width="stretch",
        )

    st.subheader("Hisse bazlı katkı")
    katkilar = sonuc.kompakt_katki_kayitlari()
    if katkilar:
        st.dataframe(
            pd.DataFrame(katkilar),
            width="stretch",
            hide_index=True,
            column_config={
                "Sembol": st.column_config.TextColumn(width="small"),
                "İşlem": st.column_config.NumberColumn(width="small"),
                "Kazanma (%)": st.column_config.NumberColumn(
                    format="%.2f%%",
                    width="small",
                ),
                "Net Kâr": st.column_config.NumberColumn(
                    format="%.2f",
                    width="medium",
                ),
                "Katkı (%)": st.column_config.NumberColumn(
                    format="%.2f%%",
                    width="small",
                ),
            },
        )

        with st.expander("İşlem hacmi ayrıntıları", expanded=False):
            st.caption(
                "Toplam ayrılan sermaye, aynı sermayenin dönem boyunca "
                "yeniden kullanıldığı kümülatif işlem hacmidir."
            )
            st.dataframe(
                pd.DataFrame(sonuc.hacim_kayitlari()),
                width="stretch",
                hide_index=True,
                column_config={
                    "Sembol": st.column_config.TextColumn(width="small"),
                    "Toplam Ayrılan Sermaye": (
                        st.column_config.NumberColumn(
                            format="%.2f",
                            width="large",
                        )
                    ),
                },
            )
    else:
        st.info("Hisse bazlı katkı kaydı bulunamadı.")

    atlanmalar = sonuc.atlanma_kayitlari()
    if atlanmalar:
        with st.expander("Atlanan işlem nedenleri", expanded=False):
            st.dataframe(
                pd.DataFrame(atlanmalar),
                width="stretch",
                hide_index=True,
            )

    portfoy_disari_aktarim_goster(sonuc)



def ayni_veri_degeri_yaz(
    metrik: SameDataComparisonMetric,
    deger: float,
) -> str:
    if metrik.birim == "para":
        return para_yaz(deger)
    if metrik.birim == "yuzde":
        return yuzde_yaz(deger)
    if metrik.birim == "sayi":
        return f"{deger:,.0f}"
    return f"{deger:,.2f}"


def ayni_veri_farki_yaz(metrik: SameDataComparisonMetric) -> str:
    if metrik.birim == "para":
        return f"{metrik.fark:+,.2f}"
    if metrik.birim == "yuzde":
        return f"{metrik.fark:+,.2f} puan"
    if metrik.birim == "sayi":
        return f"{metrik.fark:+,.0f}"
    return f"{metrik.fark:+,.2f}"


def ayni_veri_lideri_yaz(metrik: SameDataComparisonMetric) -> str:
    if metrik.lider == BAZ_ANALIZ:
        return "Baz ayar"
    if metrik.lider == KARSILASTIRMA_ANALIZI:
        return "Karşılaştırma ayarı"
    if metrik.iyilik_yonu == "notr":
        return "—"
    return "Eşit"


def ayni_veri_sonucu_goster(sonuc: SameDataComparisonResult) -> None:
    st.success(
        "Fiyat verisi bir kez alındı; iki ayar aynı veri anlık "
        "görüntüsü üzerinde çalıştırıldı."
    )
    st.caption(
        f"Dönem: {sonuc.fiyat_donemi} · "
        f"Fiyat barı: {sonuc.fiyat_bar_sayisi} · "
        f"Ortak veri kimliği: {sonuc.veri_kimligi}"
    )

    baz = sonuc.baz_sonuc.ozet
    ikinci = sonuc.karsilastirma_sonucu.ozet
    sol, sag = st.columns(2)
    with sol:
        st.subheader("Baz ayar")
        st.caption(f"Ayar kimliği: {baz.ayar_kimligi}")
        st.metric("Toplam getiri", yuzde_yaz(baz.toplam_getiri_yuzde))
        st.metric("Maksimum düşüş", yuzde_yaz(baz.maksimum_dusus_yuzde))
        st.metric("Tamamlanan işlem", str(baz.tamamlanan_islem_sayisi))
    with sag:
        st.subheader("Karşılaştırma ayarı")
        st.caption(f"Ayar kimliği: {ikinci.ayar_kimligi}")
        st.metric("Toplam getiri", yuzde_yaz(ikinci.toplam_getiri_yuzde))
        st.metric("Maksimum düşüş", yuzde_yaz(ikinci.maksimum_dusus_yuzde))
        st.metric("Tamamlanan işlem", str(ikinci.tamamlanan_islem_sayisi))

    st.subheader("Aynı veri performans farkı")
    satirlar = tuple(
        ComparisonDisplayRow(
            label=metrik.etiket,
            base_value=ayni_veri_degeri_yaz(metrik, metrik.baz_deger),
            comparison_value=ayni_veri_degeri_yaz(
                metrik, metrik.karsilastirma_degeri
            ),
            difference=ayni_veri_farki_yaz(metrik),
            leader=ayni_veri_lideri_yaz(metrik),
        )
        for metrik in sonuc.metrikler
    )
    responsive_karsilastirma_goster(satirlar)

    with st.expander("Karşılaştırma kimlikleri", expanded=False):
        st.write(
            {
                "Ortak veri kimliği": sonuc.veri_kimligi,
                "Baz analiz kimliği": baz.analiz_kimligi,
                "Baz ayar kimliği": baz.ayar_kimligi,
                "Karşılaştırma analiz kimliği": ikinci.analiz_kimligi,
                "Karşılaştırma ayar kimliği": ikinci.ayar_kimligi,
            }
        )


def ayni_veri_karsilastirma_formu() -> None:
    with st.sidebar:
        st.header("Aynı veri karşılaştırması")
        st.caption(
            "Fiyat verisi yalnızca bir kez indirilir. İki minimum skor "
            "aynı veri anlık görüntüsü üzerinde karşılaştırılır."
        )

        with st.form("ayni_veri_karsilastirma_formu"):
            sembol = st.text_input(
                "Hisse sembolü",
                value="THYAO",
                help="BIST uzantısı yazılmazsa .IS otomatik eklenir.",
            )
            indirme_donemi = st.selectbox(
                "Veri dönemi",
                options=("1y", "2y", "5y", "10y", "max"),
                index=2,
            )
            islem_gunu = st.number_input(
                "En fazla işlem günü",
                min_value=100,
                max_value=10_000,
                value=1253,
                step=50,
            )
            gorunum_etiketi = st.selectbox(
                "Teknik görünüm",
                options=tuple(GORUNUM_SECENEKLERI),
                index=0,
            )
            baz_minimum_skor = st.slider(
                "Baz minimum skor",
                min_value=0,
                max_value=100,
                value=50,
            )
            karsilastirma_minimum_skor = st.slider(
                "Karşılaştırma minimum skoru",
                min_value=0,
                max_value=100,
                value=55,
            )
            elde_tutma_gunu = st.slider(
                "Elde tutma süresi (bar)",
                min_value=1,
                max_value=30,
                value=10,
            )
            baslangic_sermayesi = st.number_input(
                "Başlangıç sermayesi",
                min_value=1_000.0,
                value=100_000.0,
                step=10_000.0,
            )
            pozisyon_yuzde = st.slider(
                "Pozisyon sermayesi (%)",
                min_value=1.0,
                max_value=100.0,
                value=100.0,
                step=1.0,
            )
            maliyet_yuzde = st.number_input(
                "İşlem maliyeti (%)",
                min_value=0.0,
                max_value=9.99,
                value=0.10,
                step=0.01,
            )
            stop_yuzde = st.number_input(
                "Zarar durdur (%)",
                min_value=0.01,
                max_value=99.0,
                value=5.0,
                step=0.5,
            )
            hedef_yuzde = st.number_input(
                "Hedef (%)",
                min_value=0.01,
                max_value=99.0,
                value=10.0,
                step=0.5,
            )
            calistirildi = st.form_submit_button(
                "Aynı veriyle karşılaştır",
                type="primary",
                width="stretch",
            )

    if not calistirildi:
        st.info(
            "Baz ve karşılaştırma skorlarını seçip sol menüdeki "
            "‘Aynı veriyle karşılaştır’ düğmesine basın."
        )
        return

    ortak = {
        "sembol": sembol,
        "islem_gunu": int(islem_gunu),
        "indirme_donemi": indirme_donemi,
        "gorunum_secimi": GORUNUM_SECENEKLERI[gorunum_etiketi],
        "elde_tutma_gunu": int(elde_tutma_gunu),
        "baslangic_sermayesi": float(baslangic_sermayesi),
        "pozisyon_yuzde": float(pozisyon_yuzde),
        "maliyet_yuzde": float(maliyet_yuzde),
        "stop_yuzde": float(stop_yuzde),
        "hedef_yuzde": float(hedef_yuzde),
    }

    try:
        baz_istek = DashboardBacktestRequest(
            **ortak,
            minimum_skor=int(baz_minimum_skor),
        )
        ikinci_istek = DashboardBacktestRequest(
            **ortak,
            minimum_skor=int(karsilastirma_minimum_skor),
        )
        with st.spinner(
            f"{baz_istek.sembol} verisi bir kez hazırlanıyor; "
            "iki ayar aynı anlık görüntüde çalışıyor..."
        ):
            sonuc = SameDataComparisonService().calistir(
                baz_istek,
                ikinci_istek,
            )
    except (ValueError, TypeError, SameDataComparisonError) as hata:
        st.error(str(hata))
        return

    baz_kayit = gecmise_kaydet(sonuc.baz_sonuc)
    ikinci_kayit = gecmise_kaydet(sonuc.karsilastirma_sonucu)
    if baz_kayit is not None and ikinci_kayit is not None:
        st.caption(
            "Her iki analiz geçmişe kaydedildi ve ortak veri kimliğiyle "
            "doğrudan karşılaştırılabilir."
        )
    ayni_veri_sonucu_goster(sonuc)


def opsiyonel_fiyat_yaz(deger: float | None) -> str:
    return "—" if deger is None else para_yaz(deger)


def aciklama_listesi_goster(
    baslik: str,
    maddeler: tuple[str, ...],
    bos_mesaj: str,
) -> None:
    st.markdown(f"**{baslik}**")
    if maddeler:
        for madde in maddeler:
            st.write(f"• {madde}")
    else:
        st.caption(bos_mesaj)




def veri_tazeligi_kilidi_goster(sonuc: DataFreshnessResult | BatchDataFreshnessResult | None) -> bool:
    """Veri tazeliğini görünür kılar; eski veride analiz sonucunu kilitler."""
    if sonuc is None:
        st.warning("Veri tazeliği doğrulanamadı. Son fiyat tarihini aracı kurumdan kontrol edin.")
        return False

    if isinstance(sonuc, BatchDataFreshnessResult):
        metrik_izgarasi_goster((
            ("Fiyat verisi durumu", sonuc.durum),
            ("Beklenen son işlem günü", str(sonuc.beklenen_tarih)),
            ("En eski fiyat tarihi", str(sonuc.en_eski_tarih or "—")),
            ("En yeni fiyat tarihi", str(sonuc.en_yeni_tarih or "—")),
            ("Güncel sembol", str(sonuc.guncel_sembol)),
            ("Eski/uyumsuz sembol", str(sonuc.eski_sembol + sonuc.veri_yok_sembol)),
        ))
    else:
        metrik_izgarasi_goster((
            ("Fiyat verisi durumu", sonuc.durum),
            ("Son fiyat veri tarihi", str(sonuc.son_veri_tarihi or "—")),
            ("Beklenen son işlem günü", str(sonuc.beklenen_tarih)),
            ("İş günü gecikmesi", str(sonuc.is_gunu_gecikmesi)),
        ))

    if sonuc.kilitli:
        st.error("VERİ TAZELİĞİ KİLİDİ: " + sonuc.aciklama)
        st.caption(f"Kilit aşaması: {sonuc.kilit_asamasi}")
        if sonuc.sonraki_kontrol_zamani is not None:
            st.caption(
                "Önerilen sonraki kontrol: "
                + tarih_saat_yaz(sonuc.sonraki_kontrol_zamani)
            )
        st.warning("Momentum sıralaması, teknik teyit, stop, hedef ve lot değerleri kullanılmamalıdır.")
        return False

    st.success(sonuc.aciklama)
    return True

def guncel_analiz_sonucu_goster(sonuc: LiveAnalysisResult) -> None:
    teknik = sonuc.teknik_teyit
    plan = sonuc.islem_plani

    st.subheader(f"{teknik.sembol} güncel teknik analiz")
    metrik_izgarasi_goster(
        (
            ("Teknik teyit skoru", f"{teknik.teyit_skoru}/100"),
            ("Teyit durumu", teknik.teyit_durumu),
            ("İşlem kararı", plan.karar),
            ("Plan tipi", plan.plan_tipi),
            ("Son kapanış", para_yaz(plan.son_kapanis)),
            ("ATR14", f"{para_yaz(plan.atr14)} · %{plan.atr_yuzde:.2f}"),
        )
    )

    zaman_tab, teyit_tab, plan_tab = st.tabs(
        ("Zaman dilimleri", "Teknik teyit", "İşlem planı")
    )

    with zaman_tab:
        satirlar = []
        for rol, zaman in (
            ("Ana trend", teknik.haftalik),
            ("Yön teyidi", teknik.gunluk),
            ("Giriş zamanlaması", teknik.saatlik),
        ):
            satirlar.append(
                {
                    "Rol": rol,
                    "Zaman": zaman.ad,
                    "Son tarih": tarih_saat_yaz(zaman.son_zaman),
                    "Kapanış": round(zaman.kapanis, 2),
                    "Skor": zaman.skor,
                    "Yön": zaman.yon,
                    "Destek": (
                        None if zaman.destek is None else round(zaman.destek, 2)
                    ),
                    "Direnç": (
                        None if zaman.direnc is None else round(zaman.direnc, 2)
                    ),
                    "Kırılım": zaman.kirilim.durum,
                    "RSI14": round(zaman.momentum.rsi14, 2),
                    "Hacim oranı": (
                        None
                        if zaman.kirilim.hacim_orani is None
                        else round(zaman.kirilim.hacim_orani, 2)
                    ),
                }
            )
        st.dataframe(
            pd.DataFrame(satirlar),
            width="stretch",
            hide_index=True,
        )
        st.caption(
            "Haftalık ana trend, günlük yön ve saatlik giriş zamanlaması "
            "birbirinden bağımsız hesaplanır."
        )

    with teyit_tab:
        for rol, zaman in (
            ("Haftalık ana trend", teknik.haftalik),
            ("Günlük yön teyidi", teknik.gunluk),
            ("Saatlik giriş zamanlaması", teknik.saatlik),
        ):
            with st.expander(
                f"{rol} · {zaman.yon} · {zaman.skor}/100",
                expanded=(rol == "Günlük yön teyidi"),
            ):
                metrik_izgarasi_goster(
                    (
                        ("EMA 9/21", zaman.ortalamalar.ema9_21_durumu),
                        ("EMA 21/55", zaman.ortalamalar.ema21_55_durumu),
                        ("SMA 50/200", zaman.ortalamalar.uzun_vade_durumu),
                        ("Momentum", zaman.momentum.durum),
                        ("Kırılım", zaman.kirilim.durum),
                        (
                            "Hacim teyidi",
                            "Var" if zaman.kirilim.hacim_teyidi else "Yok",
                        ),
                    )
                )
                aciklama_listesi_goster(
                    "Pozitif unsurlar",
                    zaman.pozitif_nedenler,
                    "Belirgin pozitif unsur yok.",
                )
                aciklama_listesi_goster(
                    "Riskler",
                    zaman.riskler,
                    "Belirgin risk yok.",
                )

        st.divider()
        aciklama_listesi_goster(
            "Ortak pozitif teyitler",
            teknik.pozitif_nedenler,
            "Belirgin ortak pozitif teyit yok.",
        )
        aciklama_listesi_goster(
            "Ortak riskler",
            teknik.riskler,
            "Belirgin ortak risk yok.",
        )

    with plan_tab:
        metrik_izgarasi_goster(
            (
                ("Karar", plan.karar),
                ("Plan tipi", plan.plan_tipi),
                ("İzleme tetik seviyesi", opsiyonel_fiyat_yaz(plan.izleme_tetik_fiyati)),
                ("Referans giriş", opsiyonel_fiyat_yaz(plan.referans_giris)),
                ("Stop-loss", opsiyonel_fiyat_yaz(plan.stop_loss)),
                ("Hedef 1", opsiyonel_fiyat_yaz(plan.hedef_1)),
                ("Hedef 2", opsiyonel_fiyat_yaz(plan.hedef_2)),
            )
        )

        if plan.giris_alt is not None:
            st.dataframe(
                pd.DataFrame(
                    (
                        {
                            "Seviye": "Giriş bölgesi",
                            "Alt": plan.giris_alt,
                            "Üst": plan.giris_ust,
                            "Kaynak": plan.giris_kaynagi,
                        },
                        {
                            "Seviye": "Stop-loss",
                            "Alt": plan.stop_loss,
                            "Üst": plan.stop_loss,
                            "Kaynak": plan.stop_kaynagi,
                        },
                        {
                            "Seviye": "Hedef 1",
                            "Alt": plan.hedef_1,
                            "Üst": plan.hedef_1,
                            "Kaynak": plan.hedef_1_kaynagi,
                        },
                        {
                            "Seviye": "Hedef 2",
                            "Alt": plan.hedef_2,
                            "Üst": plan.hedef_2,
                            "Kaynak": plan.hedef_2_kaynagi,
                        },
                    )
                ),
                width="stretch",
                hide_index=True,
            )

        if plan.pozisyon is not None:
            pozisyon = plan.pozisyon
            st.markdown("**Pozisyon büyüklüğü**")
            metrik_izgarasi_goster(
                (
                    ("Lot sayısı", str(pozisyon.lot_sayisi)),
                    ("Pozisyon tutarı", para_yaz(pozisyon.pozisyon_tutari)),
                    ("Risk bütçesi", para_yaz(pozisyon.risk_butcesi)),
                    ("Planlanan risk", para_yaz(pozisyon.planlanan_risk)),
                )
            )

        aciklama_listesi_goster(
            "Beklenen teyitler",
            plan.beklenen_teyitler,
            "Ek teyit beklenmiyor.",
        )
        aciklama_listesi_goster(
            "Planı geçersiz kılan koşullar",
            plan.gecersizlik_kosullari,
            "Ek geçersizlik koşulu yok.",
        )
        aciklama_listesi_goster(
            "Notlar",
            plan.notlar,
            "Ek not yok.",
        )

    with st.expander("Analiz kimlikleri", expanded=False):
        st.code(
            "\n".join(
                (
                    f"Veri kimliği: {teknik.veri_kimligi}",
                    f"Teknik analiz kimliği: {teknik.analiz_kimligi}",
                    f"İşlem planı kimliği: {plan.plan_kimligi}",
                )
            )
        )


def guncel_teknik_analiz_formu() -> None:
    with st.sidebar:
        st.header("Güncel teknik analiz")
        with st.form("guncel_teknik_analiz_formu"):
            sembol = st.text_input(
                "Hisse sembolü",
                value="THYAO",
                help="BIST uzantısı yazılmazsa .IS otomatik eklenir.",
            )
            sermaye = st.number_input(
                "Sermaye",
                min_value=1_000.0,
                value=100_000.0,
                step=10_000.0,
            )
            risk_yuzde = st.number_input(
                "İşlem başına azami risk (%)",
                min_value=0.10,
                max_value=10.0,
                value=1.0,
                step=0.10,
            )
            calistirildi = st.form_submit_button(
                "Güncel analizi çalıştır",
                type="primary",
                width="stretch",
            )

    if not calistirildi:
        st.info(
            "Sembol ve risk ayarlarını seçip sol menüdeki "
            "‘Güncel analizi çalıştır’ düğmesine basın."
        )
        return

    try:
        istek = LiveAnalysisRequest(
            sembol=sembol,
            sermaye=float(sermaye),
            azami_risk_orani=float(risk_yuzde) / 100.0,
        )
        with st.spinner(
            f"{istek.sembol} için saatlik, günlük ve haftalık veri hazırlanıyor..."
        ):
            sonuc = LiveAnalysisDashboardService().calistir(istek)
    except (ValueError, TypeError, LiveAnalysisDashboardError) as hata:
        st.error(str(hata))
        return

    if not veri_tazeligi_kilidi_goster(sonuc.veri_tazeligi):
        return
    guncel_analiz_sonucu_goster(sonuc)
    kayit = gecmise_kaydet(sonuc)
    if kayit is not None:
        st.caption("Güncel teknik analiz, Analiz Geçmişi'ne kaydedildi.")


def momentum_aday_ayrintisi_goster(aday: MomentumCandidate) -> None:
    st.subheader(
        f"{aday.sembol.removesuffix('.IS')} · "
        f"{aday.momentum_skoru}/100 · {aday.sinif}"
    )
    metrik_izgarasi_goster(
        (
            ("Momentum potansiyeli", f"{aday.momentum_skoru}/100"),
            ("Mevcut teknik skor", f"{aday.teknik_skor}/100"),
            ("Hacim oranı", f"{aday.hacim_orani:.2f}x"),
            ("Hacim eğimi", f"{aday.hacim_egimi:.2f}x"),
            ("Yakın direnç", f"{aday.yakin_direnc:.2f}"),
            ("Kırılım tetiği", f"{aday.kirilim_tetik_seviyesi:.2f}"),
            ("Dirence uzaklık", yuzde_yaz(aday.yirmi_gunluk_zirve_uzakligi * 100)),
            ("Risk/Getiri", f"1:{aday.risk_odul_orani:.2f}"),
            ("Listede gün", str(aday.listedeki_gun)),
            ("İlk görülmeden", yuzde_yaz(aday.ilk_gorulmeden_getiri * 100)),
        )
    )
    st.info(f"Kırılım hazırlığı: {aday.hazirlik_durumu}")
    if aday.kalici_hazirlik:
        st.warning(
            "Bu hisse günlük sınıfı zayıflasa da yakın geçmişteki tekrarlayan "
            "E0-E3 sinyalleri nedeniyle Kalıcı Hazırlık Adayı olarak izleniyor."
        )
    if aday.sinyal_gecmisi:
        st.caption("Sinyal zinciri: " + " → ".join(aday.sinyal_gecmisi))
    if aday.son_guclu_sinyal_tarihi:
        st.caption(f"Son güçlü sinyal tarihi: {aday.son_guclu_sinyal_tarihi}")
    st.caption(
        "Puan bileşenleri: "
        f"Göreceli güç {aday.goreceli_guc_puani}/20 · "
        f"Fiyat ivmesi {aday.fiyat_ivmesi_puani}/15 · "
        f"Hacim {aday.hacim_birikimi_puani}/15 · "
        f"Kırılım hazırlığı {aday.kirilim_hazirligi_puani}/15 · "
        f"Trend {aday.trend_puani}/15 · "
        f"Likidite {aday.likidite_puani}/10 · "
        f"Risk kalitesi {aday.risk_kalitesi_puani}/10"
    )
    sol, sag = st.columns(2)
    with sol:
        aciklama_listesi_goster(
            "Olumlu gerekçeler",
            aday.pozitif_nedenler,
            "Belirgin olumlu gerekçe yok.",
        )
    with sag:
        aciklama_listesi_goster(
            "Riskler",
            aday.riskler,
            "Belirgin risk yok.",
        )



def _csv_baytlari(kayitlar: tuple[dict[str, object], ...]) -> bytes:
    """Tablo kayıtlarını Excel uyumlu UTF-8 BOM içeren CSV'ye dönüştürür."""

    return pd.DataFrame(kayitlar).to_csv(
        index=False,
        lineterminator="\n",
    ).encode("utf-8-sig")


def momentum_disari_aktarim_goster(
    sonuc: MomentumDiscoveryResult,
) -> None:
    """Momentum sonucunun aday, eleme ve hata tablolarını CSV olarak sunar."""

    zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
    indirmeler: list[tuple[str, bytes, str, str]] = []

    aday_kayitlari = momentum_aday_tablosu(sonuc)
    if aday_kayitlari:
        indirmeler.append(
            (
                "Görünen adayları CSV indir",
                _csv_baytlari(aday_kayitlari),
                f"momentum_adaylari_{zaman}.csv",
                "text/csv; charset=utf-8",
            )
        )

    if sonuc.trend_politikasi_elenenler:
        indirmeler.append(
            (
                "Rejimde elenenleri CSV indir",
                _csv_baytlari(
                    tuple(
                        {
                            "Hisse": aday.sembol.removesuffix(".IS"),
                            "Sınıf": aday.sinif,
                            "Momentum": aday.momentum_skoru,
                            "Trend": aday.trend_puani,
                            "Dirence uzaklık (%)": round(
                                aday.yirmi_gunluk_zirve_uzakligi * 100,
                                2,
                            ),
                            "Neden": aday.izleme_disi_nedeni,
                        }
                        for aday in sonuc.trend_politikasi_elenenler
                    )
                ),
                f"momentum_rejim_elenenler_{zaman}.csv",
                "text/csv; charset=utf-8",
            )
        )

    if sonuc.izleme_disi:
        indirmeler.append(
            (
                "İzleme dışını CSV indir",
                _csv_baytlari(
                    tuple(
                        {
                            "Hisse": aday.sembol.removesuffix(".IS"),
                            "Momentum": aday.momentum_skoru,
                            "Neden": aday.izleme_disi_nedeni,
                        }
                        for aday in sonuc.izleme_disi
                    )
                ),
                f"momentum_izleme_disi_{zaman}.csv",
                "text/csv; charset=utf-8",
            )
        )

    if sonuc.hatalar:
        indirmeler.append(
            (
                "Hataları CSV indir",
                _csv_baytlari(
                    tuple(
                        {
                            "Hisse": hata.sembol.removesuffix(".IS"),
                            "Hata": hata.hata,
                        }
                        for hata in sonuc.hatalar
                    )
                ),
                f"momentum_hatalari_{zaman}.csv",
                "text/csv; charset=utf-8",
            )
        )

    if indirmeler:
        st.markdown("### Momentum sonucunu dışa aktar")
        indirme_dugmeleri_goster(tuple(indirmeler))


def momentum_kesif_sonucu_goster(sonuc: MomentumDiscoveryResult) -> None:
    st.subheader(f"{sonuc.evren_adi} momentum keşif taraması")

    st.markdown("### Tarama operasyon özeti")
    metrik_izgarasi_goster(
        (
            (
                "Ön tazelik kontrolü",
                "Yapıldı" if sonuc.on_tazelik_kontrolu else "Atlandı",
            ),
            (
                "Referans sembol",
                sonuc.on_tazelik_referans_sembol or "—",
            ),
            (
                "Toplu tarama",
                "Başlatıldı"
                if sonuc.toplu_tarama_baslatildi
                else "Başlatılmadı",
            ),
            (
                "Toplam süre",
                f"{sonuc.toplam_sure_saniye:.2f} sn",
            ),
            (
                "İndirilen sembol",
                str(sonuc.indirilen_sembol_sayisi),
            ),
            (
                "Analiz edilen sembol",
                str(sonuc.analiz_edilen_sembol_sayisi),
            ),
            (
                "Veri/analiz hatası",
                str(sonuc.veri_hatasi_sayisi),
            ),
            (
                "Yeniden deneme",
                str(sonuc.yeniden_deneme_sayisi),
            ),
            (
                "Veri kaynağı",
                sonuc.veri_kaynagi,
            ),
            (
                "Kilit aşaması",
                sonuc.tazelik_kilit_asamasi or "—",
            ),
            (
                "Sonraki kontrol",
                tarih_saat_yaz(sonuc.sonraki_kontrol_zamani)
                if sonuc.sonraki_kontrol_zamani
                else "—",
            ),
        )
    )

    if not veri_tazeligi_kilidi_goster(sonuc.veri_tazeligi):
        momentum_disari_aktarim_goster(sonuc)
        return

    if sonuc.piyasa_rejimi is not None:
        politika = rejime_gore_trend_politikasi(sonuc.piyasa_rejimi)
        st.markdown("### Rejim bazlı trend filtresi")
        metrik_izgarasi_goster(
            (
                ("Aktif piyasa rejimi", sonuc.piyasa_rejimi),
                ("Minimum momentum", f"{politika.minimum_momentum_skoru}/100"),
                ("Minimum trend", f"{politika.minimum_trend_puani}/15"),
                (
                    "Azami direnç uzaklığı",
                    yuzde_yaz(politika.azami_direnc_uzakligi * 100),
                ),
                ("Filtreyi geçen aday", str(len(sonuc.adaylar))),
                (
                    "Rejim nedeniyle elenen",
                    str(len(sonuc.trend_politikasi_elenenler)),
                ),
            )
        )
        if politika.kirilim_veya_yuksek_hazirlik_zorunlu:
            st.warning(
                "Riskli rejimde yalnızca kırılım veya E3/C/B düzeyinde "
                "yüksek hazırlık gösteren adaylar korunur."
            )
        else:
            st.caption(
                "Momentum, trend ve dirence uzaklık eşikleri aktif piyasa "
                "rejimine göre uygulanmıştır."
            )
    else:
        st.info(
            "Rejim bazlı trend filtresi kapalı. Adaylar yalnızca momentum "
            "keşif koşullarıyla sıralandı."
        )

    metrik_izgarasi_goster(
        (
            ("Tarama evreni", str(sonuc.evren_sembol_sayisi)),
            ("Başarılı analiz", str(sonuc.basarili_sayisi)),
            ("C — İşleme hazır", str(sonuc.isleme_hazir_sayisi)),
            ("B — Kırılım", str(sonuc.kirilim_sayisi)),
            ("E3 — Erken uyarı", str(sonuc.sinif_sayisi(SINIF_ERKEN_UYARI))),
            ("E2 — Dirence yakın", str(sonuc.sinif_sayisi(SINIF_DIRENCE_YAKLASIYOR))),
            ("E1 — Hacim birikimi", str(sonuc.sinif_sayisi(SINIF_HACIM_BIRIKIMI))),
            ("E0 — Sıkışma", str(sonuc.sinif_sayisi(SINIF_SIKISMA))),
            ("K — Kalıcı hazırlık", str(sonuc.sinif_sayisi(SINIF_KALICI_HAZIRLIK))),
            ("D — Aşırı yükselmiş", str(len(sonuc.asiri_yukselmisler))),
        )
    )
    st.caption(
        f"Evren kaynağı: {sonuc.evren_kaynagi} · "
        f"Bileşen tarihi: {sonuc.evren_tarihi}"
    )
    st.info(
        "Momentum skoru bir erken keşif ölçüsüdür; doğrudan alım kararı "
        "değildir. C sınıfı adaylar bile ayrıntılı Güncel Teknik Analiz "
        "ekranında yeniden doğrulanmalıdır. KAP/haber katalizörü bu sürümde "
        "otomatik puanlanmaz ve ayrıca kontrol edilmelidir."
    )

    kayitlar = momentum_aday_tablosu(sonuc)
    if not kayitlar:
        st.warning(
            "Seçilen minimum skoru ve A/B/C sınıflarını karşılayan aday "
            "bulunamadı. Minimum skoru azaltmak yerine evreni ve piyasa "
            "koşullarını yeniden değerlendirin."
        )
    else:
        st.dataframe(
            pd.DataFrame(kayitlar),
            width="stretch",
            hide_index=True,
            column_config={
                "Sıra": st.column_config.NumberColumn(width="small"),
                "Hisse": st.column_config.TextColumn(width="small"),
                "Sınıf": st.column_config.TextColumn(width="large"),
                "Momentum": st.column_config.NumberColumn(width="small"),
                "Teknik": st.column_config.NumberColumn(width="small"),
                "Son kapanış": st.column_config.NumberColumn(format="%.2f"),
                "5G (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "20G (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Hacim": st.column_config.NumberColumn(format="%.2fx"),
                "Yakın direnç": st.column_config.NumberColumn(format="%.2f"),
                "Kırılım tetiği": st.column_config.NumberColumn(format="%.2f"),
                "Dirence uzaklık (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Hacim eğimi": st.column_config.NumberColumn(format="%.2fx"),
                "Göreceli güç eğimi (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Risk/Getiri": st.column_config.NumberColumn(format="1:%.2f"),
                "İlk görülmeden (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
        secili = st.selectbox(
            "Momentum aday ayrıntısı",
            options=temel_filtre_sonucu.accepted,
            format_func=lambda aday: (
                f"{aday.sembol.removesuffix('.IS')} · "
                f"{aday.momentum_skoru}/100 · {aday.sinif}"
            ),
            key="momentum_kesif_aday_ayrintisi",
        )
        momentum_aday_ayrintisi_goster(secili)

    if sonuc.asiri_yukselmisler:
        with st.expander("D — Aşırı yükselmiş / peşinden koşulmaması gerekenler"):
            st.dataframe(
                pd.DataFrame(
                    {
                        "Hisse": aday.sembol.removesuffix(".IS"),
                        "Momentum": aday.momentum_skoru,
                        "5G (%)": round(aday.getiri_5g * 100, 2),
                        "RSI14": round(aday.rsi14, 2),
                        "Risk": " | ".join(aday.riskler),
                    }
                    for aday in sonuc.asiri_yukselmisler
                ),
                width="stretch",
                hide_index=True,
            )

    if sonuc.trend_politikasi_elenenler:
        with st.expander(
            "Piyasa rejimi filtresinde elenen hisseler ve nedenleri",
            expanded=False,
        ):
            st.dataframe(
                pd.DataFrame(
                    {
                        "Hisse": aday.sembol.removesuffix(".IS"),
                        "Sınıf": aday.sinif,
                        "Momentum": aday.momentum_skoru,
                        "Trend": f"{aday.trend_puani}/15",
                        "Dirence uzaklık (%)": round(
                            aday.yirmi_gunluk_zirve_uzakligi * 100,
                            2,
                        ),
                        "Neden": aday.izleme_disi_nedeni,
                    }
                    for aday in sonuc.trend_politikasi_elenenler
                ),
                width="stretch",
                hide_index=True,
            )

    if sonuc.izleme_disi:
        with st.expander("İzleme Dışı kalan hisseler ve nedenleri"):
            st.dataframe(
                pd.DataFrame(
                    {
                        "Hisse": aday.sembol.removesuffix(".IS"),
                        "Momentum": aday.momentum_skoru,
                        "Son kapanış": round(aday.kapanis, 2),
                        "Yakın direnç": round(aday.yakin_direnc, 2),
                        "Dirence uzaklık (%)": round(
                            aday.yirmi_gunluk_zirve_uzakligi * 100, 2
                        ),
                        "Neden": aday.izleme_disi_nedeni,
                        "Sinyal geçmişi": " → ".join(aday.sinyal_gecmisi),
                    }
                    for aday in sonuc.izleme_disi
                ),
                width="stretch",
                hide_index=True,
            )

    if sonuc.hatalar:
        with st.expander("Verisi alınamayan veya analiz edilemeyen hisseler"):
            st.dataframe(
                pd.DataFrame(
                    {
                        "Hisse": hata.sembol.removesuffix(".IS"),
                        "Hata": hata.hata,
                    }
                    for hata in sonuc.hatalar
                ),
                width="stretch",
                hide_index=True,
            )
    if sonuc.kayit_yolu:
        st.caption(f"Momentum tarama geçmişi kaydedildi: {sonuc.kayit_yolu}")

    momentum_disari_aktarim_goster(sonuc)


def momentum_walk_forward_sonucu_goster(sonuc: MomentumWalkForwardResult) -> None:
    st.subheader(
        f"{sonuc.evren_adi} tarihsel yeniden oynatma · {sonuc.kesim_tarihi}"
    )
    metrik_izgarasi_goster(
        (
            ("Tarama evreni", str(sonuc.evren_sembol_sayisi)),
            ("Kesimde analiz", str(sonuc.basarili_sayisi)),
            ("Gösterilen aday", str(len(sonuc.sonuclar))),
            ("İzleme dışı", str(len(sonuc.izleme_disi))),
            ("20 bar içinde ≥%10", str(sonuc.guclu_hareket_sayisi)),
        )
    )
    st.info(
        "Kesim tarihinden sonraki fiyatlar aday üretiminde kullanılmaz. "
        "5/10/20 günlük kapanış getirileri ile dönem içi en yüksek/düşük "
        "fiyatlar yalnızca sonradan performans ölçümü için hesaplanır."
    )
    if sonuc.sinyal_gecmisi_hesaplandi:
        st.caption(
            "Küçük özel/kayıtlı listelerde son altı haftalık sınıf zinciri "
            "otomatik hesaplanmıştır."
        )

    kayitlar = walk_forward_tablosu(sonuc)
    if kayitlar:
        st.dataframe(
            pd.DataFrame(kayitlar),
            width="stretch",
            hide_index=True,
            column_config={
                "Sinyal fiyatı": st.column_config.NumberColumn(format="%.2f"),
                "Yakın direnç": st.column_config.NumberColumn(format="%.2f"),
                "Kırılım tetiği": st.column_config.NumberColumn(format="%.2f"),
                "Dirence uzaklık (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "5G kapanış (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "10G kapanış (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "20G kapanış (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Dönem içi en yüksek": st.column_config.NumberColumn(format="%.2f"),
                "Gerçek azami yükseliş (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Dönem içi en düşük": st.column_config.NumberColumn(format="%.2f"),
                "Azami ters hareket (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )
        secili = st.selectbox(
            "Tarihsel aday ayrıntısı",
            options=sonuc.sonuclar,
            format_func=lambda item: (
                f"{item.aday.sembol.removesuffix('.IS')} · "
                f"{item.aday.momentum_skoru}/100 · {item.aday.sinif}"
            ),
            key="momentum_walk_forward_aday_ayrintisi",
        )
        st.markdown("**İleri dönem fiyat aralığı**")
        metrik_izgarasi_goster(
            (
                ("Sinyal fiyatı", f"{secili.aday.kapanis:.2f}"),
                ("En yüksek fiyat", f"{secili.maksimum_fiyat:.2f}" if secili.maksimum_fiyat is not None else "-"),
                ("En yüksek tarih", secili.maksimum_fiyat_tarihi or "-"),
                ("Gerçek azami yükseliş", yuzde_yaz((secili.maksimum_olumlu_hareket or 0.0) * 100)),
                ("En düşük fiyat", f"{secili.minimum_fiyat:.2f}" if secili.minimum_fiyat is not None else "-"),
                ("Azami ters hareket", yuzde_yaz((secili.maksimum_ters_hareket or 0.0) * 100)),
                ("Yakın direnç", f"{secili.aday.yakin_direnc:.2f}"),
                ("Kırılım tetiği", f"{secili.aday.kirilim_tetik_seviyesi:.2f}"),
            )
        )
        st.markdown("**Güncel seans karşılaştırması**")
        st.caption(
            "Bu karttaki gün içi veri, tarihsel aday üretimine ve walk-forward "
            "sonucuna katılmaz; yalnızca tamamlanmış barlarla güncel seansı "
            "ayrı karşılaştırmak için kullanılır."
        )
        canli_key = f"momentum_canli_seans_{secili.aday.sembol}"
        if st.button(
            "Güncel seans verisini getir",
            key=f"{canli_key}_dugme",
        ):
            try:
                with st.spinner(f"{secili.aday.sembol.removesuffix('.IS')} güncel seansı alınıyor..."):
                    st.session_state[canli_key] = guncel_seans_ozeti_getir(
                        secili.aday.sembol
                    )
            except (CurrentSessionSnapshotError, ValueError) as hata:
                st.session_state.pop(canli_key, None)
                st.warning(str(hata))

        canli = st.session_state.get(canli_key)
        if canli is not None:
            if not canli.bugunku_seans:
                st.warning(
                    "Veri sağlayıcı bugünkü seansı henüz döndürmedi. "
                    f"Gösterilen son mevcut seans: {canli.seans_tarihi}."
                )
            canli_azami = canli.azami_getiri(secili.aday.kapanis)
            canli_son = canli.son_getiri(secili.aday.kapanis)
            canli_ters = canli.azami_ters_hareket(secili.aday.kapanis)
            metrik_izgarasi_goster(
                (
                    ("Seans tarihi", canli.seans_tarihi),
                    ("Son veri zamanı", canli.son_veri_zamani),
                    ("Son fiyat", f"{canli.son_fiyat:.2f}"),
                    ("Gün içi en yüksek", f"{canli.en_yuksek:.2f}"),
                    ("Gün içi en düşük", f"{canli.en_dusuk:.2f}"),
                    (
                        "Sinyale göre son getiri",
                        yuzde_yaz((canli_son or 0.0) * 100),
                    ),
                    (
                        "Canlı seans dâhil azami yükseliş",
                        yuzde_yaz((canli_azami or 0.0) * 100),
                    ),
                    (
                        "Canlı seans ters hareketi",
                        yuzde_yaz((canli_ters or 0.0) * 100),
                    ),
                )
            )
            if (
                secili.maksimum_fiyat is not None
                and canli.en_yuksek > secili.maksimum_fiyat
            ):
                fark = canli.en_yuksek - secili.maksimum_fiyat
                st.success(
                    "Güncel seans tepesi, tamamlanmış barlara dayalı tarihsel "
                    f"tepenin {fark:.2f} üzerinde."
                )

        gecmis_kayitlari = sinyal_gecmisi_tablosu(secili)
        if gecmis_kayitlari:
            st.markdown("**Sinyal sınıfı geçmişi**")
            st.dataframe(
                pd.DataFrame(gecmis_kayitlari),
                width="stretch",
                hide_index=True,
            )
    else:
        st.warning("Kesim tarihinde seçilen koşulları karşılayan aday bulunamadı.")

    izleme_disi = walk_forward_izleme_disi_tablosu(sonuc)
    if izleme_disi:
        with st.expander("Kesimde İzleme Dışı kalan hisseler ve nedenleri"):
            st.dataframe(
                pd.DataFrame(izleme_disi),
                width="stretch",
                hide_index=True,
            )
    if sonuc.hatalar:
        with st.expander("Yeniden oynatmada değerlendirilemeyen hisseler"):
            st.dataframe(
                pd.DataFrame(
                    {
                        "Hisse": hata.sembol.removesuffix(".IS"),
                        "Hata": hata.hata,
                    }
                    for hata in sonuc.hatalar
                ),
                width="stretch",
                hide_index=True,
            )

PIYASA_REJIMI_BAGLAMI_KEY = "aktif_piyasa_rejimi_baglami"


def piyasa_rejimi_baglami_dogrula(
    ham_baglam: object,
    *,
    bugun: date | None = None,
) -> tuple[dict[str, object] | None, str | None]:
    """Oturumdaki rejim bağlamının güncel ve doğrulanmış olduğunu kontrol eder."""

    if not isinstance(ham_baglam, dict):
        return None, (
            "Doğrulanmış piyasa rejimi bulunmuyor. "
            "Önce Piyasa Rejimi ekranında güncel analiz çalıştırın."
        )

    gerekli_alanlar = (
        "rejim",
        "analiz_tarihi",
        "guven_duzeyi",
        "kaynak",
        "veri_durumu",
        "beklenen_tarih",
        "olusturulma_tarihi",
        "gecerli",
    )
    eksikler = tuple(
        alan for alan in gerekli_alanlar
        if alan not in ham_baglam
    )
    if eksikler:
        return None, (
            "Piyasa rejimi bağlamı eksik olduğu için filtre kapatıldı."
        )

    rejim = str(ham_baglam.get("rejim", ""))
    if rejim not in (REJIM_POZITIF, REJIM_SECICI, REJIM_RISKLI):
        return None, (
            "Piyasa rejimi değeri desteklenmediği için filtre kapatıldı."
        )

    if not bool(ham_baglam.get("gecerli")):
        neden = str(
            ham_baglam.get("gecersizlik_nedeni")
            or "Piyasa rejimi doğrulanamadı."
        )
        return None, neden

    if str(ham_baglam.get("veri_durumu")) != "Güncel":
        return None, (
            "Piyasa rejimi verisi güncel olmadığı için filtre kapatıldı."
        )

    bugun_degeri = bugun or date.today()
    if str(ham_baglam.get("olusturulma_tarihi")) != bugun_degeri.isoformat():
        return None, (
            "Oturumdaki piyasa rejimi önceki güne ait. "
            "Rejimi yeniden analiz edin."
        )

    for alan in ("analiz_tarihi", "guven_duzeyi", "kaynak"):
        if not str(ham_baglam.get(alan, "")).strip():
            return None, (
                "Piyasa rejimi kaynağı, tarihi veya güven düzeyi eksik."
            )

    return dict(ham_baglam), None


def piyasa_rejimi_baglami_imzasi(
    baglam: dict[str, object] | None,
) -> tuple[object, ...] | None:
    if baglam is None:
        return None
    return (
        baglam.get("rejim"),
        baglam.get("analiz_tarihi"),
        baglam.get("guven_duzeyi"),
        baglam.get("kaynak"),
        baglam.get("beklenen_tarih"),
        baglam.get("olusturulma_tarihi"),
    )


MOMENTUM_REPLAY_RESULT_KEY = "momentum_walk_forward_sonucu"
MOMENTUM_REPLAY_SIGNATURE_KEY = "momentum_walk_forward_imzasi"
MOMENTUM_DISCOVERY_RESULT_KEY = "momentum_kesif_sonucu"
MOMENTUM_DISCOVERY_SIGNATURE_KEY = "momentum_kesif_imzasi"


def momentum_walk_forward_oturum_imzasi(
    *,
    evren: str,
    semboller: list[str],
    minimum_skor: int,
    maksimum_aday: int,
    internetten_guncelle: bool,
    kesim_tarihi: date,
) -> tuple[object, ...]:
    """Yeniden oynatma sonucunun mevcut sol menü ayarlarıyla eşleşmesini sağlar."""

    return (
        evren,
        tuple(semboller),
        int(minimum_skor),
        int(maksimum_aday),
        bool(internetten_guncelle),
        kesim_tarihi.isoformat(),
    )



def momentum_kesif_oturum_imzasi(
    *,
    evren: str,
    semboller: list[str],
    minimum_skor: int,
    maksimum_aday: int,
    internetten_guncelle: bool,
    piyasa_rejimi: str | None,
    rejim_baglami_imzasi: tuple[object, ...] | None,
) -> tuple[object, ...]:
    """Momentum sonucunu yalnızca aynı ayarlarla yeniden gösterir."""

    return (
        evren,
        tuple(semboller),
        int(minimum_skor),
        int(maksimum_aday),
        bool(internetten_guncelle),
        piyasa_rejimi,
        rejim_baglami_imzasi,
    )


def momentum_kesif_formu() -> None:
    with st.sidebar:
        st.header("Momentum keşif")
        st.caption(
            "BIST evrenini göreceli güç, fiyat ivmesi, hacim birikimi, "
            "sıkışma ve kırılım hazırlığıyla tarar."
        )
        # Geriye dönük kaynak-test uyumluluğu için eski anahtar okunur;
        # güvenlik kararında kullanılmaz. Geçerli kaynak yalnızca tarihli
        # PIYASA_REJIMI_BAGLAMI_KEY bağlamıdır.
        _eski_rejim_uyumluluk = st.session_state.get("aktif_piyasa_rejimi")
        rejim_baglami, rejim_baglami_hatasi = (
            piyasa_rejimi_baglami_dogrula(
                st.session_state.get(PIYASA_REJIMI_BAGLAMI_KEY)
            )
        )
        kayitli_rejim = (
            str(rejim_baglami["rejim"])
            if rejim_baglami is not None
            else None
        )
        rejim_secenekleri = (
            "Kapalı",
            REJIM_POZITIF,
            REJIM_SECICI,
            REJIM_RISKLI,
        )
        varsayilan_rejim = (
            kayitli_rejim
            if kayitli_rejim in rejim_secenekleri
            else "Kapalı"
        )
        piyasa_rejimi_secimi = st.selectbox(
            "Piyasa rejimi filtresi",
            options=rejim_secenekleri,
            index=rejim_secenekleri.index(varsayilan_rejim),
            disabled=rejim_baglami is None,
            help=(
                "Yalnızca bugün üretilmiş, güncel ve doğrulanmış piyasa "
                "rejimi otomatik kullanılabilir."
            ),
            key="momentum_piyasa_rejimi",
        )
        if rejim_baglami is not None:
            st.caption(
                "Rejim bağlamı: "
                f"{rejim_baglami['kaynak']} · "
                f"{tarih_saat_yaz(rejim_baglami['analiz_tarihi'])} · "
                f"Güven: {rejim_baglami['guven_duzeyi']}"
            )
        elif rejim_baglami_hatasi:
            st.caption("Rejim filtresi kapalı: " + rejim_baglami_hatasi)
        # Bu kontroller form dışında tutulur. Streamlit formundaki widget değişiklikleri
        # gönderimden önce yeniden çalıştırılmadığı için, tarih alanı işaretli kutuya
        # rağmen pasif kalabiliyordu. Form dışındaki kontroller anında tepki verir.
        evren = st.selectbox(
            "Keşif evreni",
            options=TARAMA_EVRENLERI,
            index=TARAMA_EVRENLERI.index("BIST Tüm"),
            key="momentum_evreni",
        )
        ozel_liste = st.text_area(
            "Özel keşif listesi",
            value="THYAO, ASELS, TUPRS, SAHOL, KCHOL",
            height=90,
            help=(
                "Bu alan yalnızca Özel Liste evreninde kullanılır. "
                "Virgül, boşluk veya yeni satırla ayırabilirsiniz."
            ),
        )
        minimum_skor = st.slider(
            "Minimum momentum skoru",
            min_value=40,
            max_value=85,
            value=55,
        )
        maksimum_aday = st.slider(
            "Gösterilecek aday sayısı",
            min_value=5,
            max_value=50,
            value=25,
        )
        internetten_guncelle = st.checkbox(
            "BIST evrenini resmi kaynaktan güncelle",
            value=True,
            disabled=(
                evren not in ("BIST 30", "BIST 100", "BIST 500", "BIST Tüm")
            ),
        )
        yeniden_oynat = st.checkbox(
            "Tarihsel yeniden oynatma (walk-forward)",
            value=False,
            help=(
                "Kesim tarihinden sonraki fiyatları aday üretiminden gizler ve "
                "adayların sonraki 5/10/20 günlük performansını ölçer."
            ),
            key="momentum_yeniden_oynat",
        )
        kesim_tarihi = st.date_input(
            "Kesim tarihi",
            value=date.today() - timedelta(days=45),
            max_value=date.today() - timedelta(days=1),
            disabled=not yeniden_oynat,
            key="momentum_kesim_tarihi",
        )
        calistirildi = st.button(
            "Tarihsel testi başlat" if yeniden_oynat else "Momentum keşfini başlat",
            type="primary",
            width="stretch",
            key="momentum_kesif_calistir",
        )

    semboller = ozel_sembol_metinini_ayristir(ozel_liste)
    aktif_rejim = (
        None
        if (
            rejim_baglami is None
            or piyasa_rejimi_secimi == "Kapalı"
        )
        else piyasa_rejimi_secimi
    )
    discovery_imzasi = momentum_kesif_oturum_imzasi(
        evren=evren,
        semboller=semboller,
        minimum_skor=int(minimum_skor),
        maksimum_aday=int(maksimum_aday),
        internetten_guncelle=bool(internetten_guncelle),
        piyasa_rejimi=aktif_rejim,
        rejim_baglami_imzasi=piyasa_rejimi_baglami_imzasi(
            rejim_baglami
        ),
    )
    replay_imzasi = momentum_walk_forward_oturum_imzasi(
        evren=evren,
        semboller=semboller,
        minimum_skor=int(minimum_skor),
        maksimum_aday=int(maksimum_aday),
        internetten_guncelle=bool(internetten_guncelle),
        kesim_tarihi=kesim_tarihi,
    )

    if rejim_baglami is None:
        st.warning(
            "Piyasa rejimi filtresi otomatik olarak Kapalı tutuluyor. "
            + str(rejim_baglami_hatasi)
        )
    else:
        st.info(
            "Doğrulanmış piyasa rejimi bağlamı: "
            f"{rejim_baglami['rejim']} · "
            f"Kaynak {rejim_baglami['kaynak']} · "
            f"Veri {tarih_saat_yaz(rejim_baglami['analiz_tarihi'])} · "
            f"Güven {rejim_baglami['guven_duzeyi']}"
        )

    if not calistirildi:
        kayitli_replay = st.session_state.get(MOMENTUM_REPLAY_RESULT_KEY)
        kayitli_imza = st.session_state.get(MOMENTUM_REPLAY_SIGNATURE_KEY)
        if (
            yeniden_oynat
            and kayitli_imza == replay_imzasi
            and isinstance(kayitli_replay, MomentumWalkForwardResult)
        ):
            # Güncel seans düğmesi Streamlit yeniden çalışması başlatır.
            # Tarihsel sonuç oturumda saklanmazsa bu yeniden çalışmada sonuç
            # ekranı kaybolur ve düğme olayı işlenemez.
            momentum_walk_forward_sonucu_goster(kayitli_replay)
            return
        kayitli_sonuc = st.session_state.get(
            MOMENTUM_DISCOVERY_RESULT_KEY
        )
        kayitli_discovery_imzasi = st.session_state.get(
            MOMENTUM_DISCOVERY_SIGNATURE_KEY
        )
        if (
            not yeniden_oynat
            and kayitli_discovery_imzasi == discovery_imzasi
            and isinstance(kayitli_sonuc, MomentumDiscoveryResult)
        ):
            momentum_kesif_sonucu_goster(kayitli_sonuc)
            return

        if (
            kayitli_discovery_imzasi is not None
            and kayitli_discovery_imzasi != discovery_imzasi
        ):
            st.session_state.pop(MOMENTUM_DISCOVERY_RESULT_KEY, None)
            st.session_state.pop(MOMENTUM_DISCOVERY_SIGNATURE_KEY, None)
            st.info(
                "Momentum ayarları değiştiği için önceki sonuç geçersiz "
                "kılındı. Yeni ayarlarla taramayı başlatın."
            )
            return

        st.info(
            "Keşif evrenini seçip sol menüdeki başlat düğmesine basın. "
            "Tarihsel yeniden oynatma, gelecek veriyi gizleyerek erken uyarı "
            "başarısını ölçer."
        )
        return

    if yeniden_oynat:
        st.session_state.pop(MOMENTUM_DISCOVERY_RESULT_KEY, None)
        st.session_state.pop(MOMENTUM_DISCOVERY_SIGNATURE_KEY, None)
        try:
            istek_replay = MomentumWalkForwardRequest(
                evren=evren,
                kesim_tarihi=kesim_tarihi.isoformat(),
                maksimum_aday=int(maksimum_aday),
                minimum_skor=int(minimum_skor),
                ozel_semboller=semboller,
                internetten_evren_guncelle=bool(internetten_guncelle),
            )
            with st.spinner(
                f"{istek_replay.evren} {istek_replay.kesim_tarihi} "
                "tarihinde yeniden oynatılıyor..."
            ):
                replay_sonucu = MomentumWalkForwardService().calistir(istek_replay)
        except (ValueError, TypeError, MomentumWalkForwardError) as hata:
            st.error(str(hata))
            return
        st.session_state[MOMENTUM_REPLAY_RESULT_KEY] = replay_sonucu
        st.session_state[MOMENTUM_REPLAY_SIGNATURE_KEY] = replay_imzasi
        momentum_walk_forward_sonucu_goster(replay_sonucu)
        return

    st.session_state.pop(MOMENTUM_REPLAY_RESULT_KEY, None)
    st.session_state.pop(MOMENTUM_REPLAY_SIGNATURE_KEY, None)
    ilerleme = st.progress(0, text="Momentum keşfi hazırlanıyor...")
    durum = st.empty()

    def ilerleme_bildir(sira: int, toplam: int, sembol: str) -> None:
        oran = min(max(sira / toplam, 0.0), 1.0)
        ilerleme.progress(
            oran,
            text=f"[{sira}/{toplam}] {sembol} momentum analizi...",
        )
        durum.caption(f"Son işlenen hisse: {sembol}")

    def durum_bildir(mesaj: str) -> None:
        durum.info(mesaj)

    try:
        istek = MomentumDiscoveryRequest(
            evren=evren,
            maksimum_aday=int(maksimum_aday),
            minimum_skor=int(minimum_skor),
            ozel_semboller=semboller,
            internetten_evren_guncelle=bool(internetten_guncelle),
            piyasa_rejimi=(
                aktif_rejim
            ),
        )
        with st.spinner(f"{istek.evren} momentum potansiyeli taranıyor..."):
            sonuc = MomentumDiscoveryService().calistir(
                istek,
                ilerleme_bildirimi=ilerleme_bildir,
                durum_bildirimi=durum_bildir,
            )
    except (ValueError, TypeError, MomentumDiscoveryError) as hata:
        ilerleme.empty()
        durum.empty()
        st.error(str(hata))
        return

    if sonuc.veri_tazeligi is not None and sonuc.veri_tazeligi.kilitli:
        ilerleme.progress(
            1.0,
            text="Veri tazeliği kilidi nedeniyle tarama durduruldu.",
        )
    else:
        ilerleme.progress(1.0, text="Momentum keşfi tamamlandı.")
    durum.empty()
    st.session_state[MOMENTUM_DISCOVERY_RESULT_KEY] = sonuc
    st.session_state[MOMENTUM_DISCOVERY_SIGNATURE_KEY] = discovery_imzasi
    momentum_kesif_sonucu_goster(sonuc)


def vbts_yonetim_paneli_goster() -> bool:
    csv_path = configured_vbts_csv_path()
    tarama_hazir = True

    with st.expander("VBTS kayıt yönetimi", expanded=False):
        st.caption(
            "Yalnızca resmî KAP bildirimlerinden doğrulanmış tedbirleri girin. "
            "Taramada sadece bugün aktif olan kayıtlar kullanılır."
        )

        try:
            lifecycle = synchronize_vbts_operational_state(csv_path)
            records = list_vbts_records(csv_path)
            operational = read_operational_status(csv_path, lifecycle)
        except DashboardVbtsManagerError as hata:
            tarama_hazir = False
            st.error(
                "VBTS otomatik senkronizasyonu başarısız — "
                "Toplu tarama güvenlik nedeniyle kilitli."
            )
            st.caption(str(hata))
            records = ()
            lifecycle = classify_vbts_records(())
            operational = None


        try:
            health = validate_vbts_system_health(csv_path)
        except DashboardVbtsManagerError as hata:
            tarama_hazir = False
            health = None
            st.error(
                "VBTS sistem sağlık kontrolü tamamlanamadı — "
                "Toplu tarama güvenlik nedeniyle kilitli."
            )
            st.caption(str(hata))

        if health is not None:
            if health.healthy:
                st.success("VBTS sistem sağlığı: Sağlıklı")
            else:
                tarama_hazir = False
                st.error(
                    "VBTS sistem sağlığı: Sorunlu — "
                    "Toplu tarama güvenlik nedeniyle kilitli."
                )
            metrik_izgarasi_goster(
                (
                    ("Kayıt arşivi", health.registry_status),
                    ("Aktif CSV", health.active_csv_status),
                    ("Yedek bütünlüğü", health.backup_status),
                    ("Denetim günlüğü", health.audit_status),
                )
            )
            for message in health.messages:
                st.caption(f"• {message}")

        metrik_izgarasi_goster(
            (
                ("Aktif kayıt", str(len(lifecycle.active))),
                ("Gelecekte başlayacak", str(len(lifecycle.future))),
                ("Süresi dolmuş", str(len(lifecycle.expired))),
                ("Toplam arşiv kaydı", str(len(records))),
            )
        )

        if operational is not None:
            st.caption(f"Son otomatik senkronizasyon: {operational.synchronized_at}")
            st.caption(
                "Son VBTS işlemi: "
                + (
                    f"{operational.last_action} · {operational.last_action_at}"
                    if operational.last_action
                    else "Henüz kayıtlı işlem yok"
                )
            )
            st.caption(f"Denetim günlüğü: {operational.audit_log_path}")

        if records:
            st.dataframe(
                pd.DataFrame(record.as_display_row() for record in records),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Kayıtlı VBTS tedbiri bulunmuyor.")

        if lifecycle.expired:
            st.warning(
                "Süresi dolmuş kayıtlar arşivde tutuluyor ancak toplu tarama "
                "filtresine dahil edilmiyor."
            )
            cleanup_confirmed = st.checkbox(
                "Süresi dolmuş kayıtların kalıcı olarak silinmesini onaylıyorum.",
                value=False,
                key="vbts_suresi_dolmus_temizlik_onayi",
            )
            cleanup_requested = st.button(
                "Süresi dolmuş kayıtları temizle",
                width="stretch",
                disabled=not cleanup_confirmed,
                key="vbts_suresi_dolmus_temizle",
            )
            if cleanup_requested:
                try:
                    remaining = purge_expired_vbts_records(csv_path)
                except DashboardVbtsManagerError as hata:
                    tarama_hazir = False
                    st.error(str(hata))
                else:
                    st.session_state["vbts_yonetim_bildirimi"] = (
                        "Süresi dolmuş VBTS kayıtları temizlendi. "
                        f"Kalan arşiv kaydı: {len(remaining)}"
                    )
                    st.rerun()


        st.divider()
        with st.expander("VBTS yedekleri ve denetim günlüğü", expanded=False):
            st.caption(
                "Yedek geri yükleme mevcut VBTS kayıt arşivini değiştirir. "
                "Geri yükleme öncesinde mevcut arşiv ayrıca yedeklenir."
            )

            try:
                backups = list_vbts_backups(csv_path)
                audit_events = read_audit_events(csv_path, limit=50)
            except DashboardVbtsManagerError as hata:
                tarama_hazir = False
                st.error(
                    "VBTS yedek veya denetim verisi doğrulanamadı — "
                    "Toplu tarama güvenlik nedeniyle kilitli."
                )
                st.caption(str(hata))
                backups = ()
                audit_events = ()

            if backups:
                backup_map = {
                    (
                        f"{item.created_at} · {item.record_count} kayıt · "
                        f"{item.file_name}"
                    ): item
                    for item in backups
                }
                selected_backup_label = st.selectbox(
                    "Geri yüklenecek VBTS yedeği",
                    options=tuple(backup_map),
                    key="vbts_geri_yuklenecek_yedek",
                )
                selected_backup = backup_map[selected_backup_label]

                try:
                    preview_records, preview_lifecycle = inspect_vbts_backup(
                        csv_path,
                        selected_backup.path,
                    )
                except DashboardVbtsManagerError as hata:
                    tarama_hazir = False
                    st.error(f"Seçilen VBTS yedeği doğrulanamadı: {hata}")
                else:
                    metrik_izgarasi_goster(
                        (
                            ("Yedekteki kayıt", str(len(preview_records))),
                            ("Aktif olacak", str(len(preview_lifecycle.active))),
                            (
                                "Gelecekte başlayacak",
                                str(len(preview_lifecycle.future)),
                            ),
                            (
                                "Süresi dolmuş",
                                str(len(preview_lifecycle.expired)),
                            ),
                        )
                    )
                    st.dataframe(
                        pd.DataFrame(
                            record.as_display_row()
                            for record in preview_records
                        ),
                        width="stretch",
                        hide_index=True,
                    )

                    restore_confirmed = st.checkbox(
                        "Seçilen yedeğin mevcut VBTS arşivinin yerine "
                        "geri yüklenmesini onaylıyorum.",
                        value=False,
                        key="vbts_yedek_geri_yukleme_onayi",
                    )
                    restore_text = st.text_input(
                        "Onaylamak için GERİ YÜKLE yazın",
                        value="",
                        key="vbts_yedek_geri_yukleme_metni",
                    )
                    restore_ready = (
                        restore_confirmed
                        and restore_text.strip().upper() == "GERİ YÜKLE"
                    )
                    restore_requested = st.button(
                        "Seçilen VBTS yedeğini geri yükle",
                        type="primary",
                        width="stretch",
                        disabled=not restore_ready,
                        key="vbts_yedegi_geri_yukle",
                    )
                    if restore_requested:
                        try:
                            restored = restore_vbts_backup(
                                csv_path,
                                selected_backup.path,
                            )
                        except DashboardVbtsManagerError as hata:
                            tarama_hazir = False
                            st.error(
                                "VBTS yedeği geri yüklenemedi — "
                                "Toplu tarama güvenlik nedeniyle kilitli."
                            )
                            st.caption(str(hata))
                        else:
                            st.session_state["vbts_yonetim_bildirimi"] = (
                                f"{len(restored)} VBTS kaydı yedekten "
                                "geri yüklendi."
                            )
                            st.rerun()
            else:
                st.info(
                    "Geri yüklenebilir VBTS kayıt arşivi yedeği bulunmuyor."
                )

            st.markdown("**Son denetim işlemleri**")
            if audit_events:
                st.dataframe(
                    pd.DataFrame(audit_display_rows(audit_events)),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("Henüz VBTS denetim kaydı bulunmuyor.")

            if audit_events:
                st.download_button(
                    "Denetim günlüğünü CSV indir",
                    data=audit_events_csv_bytes(audit_events),
                    file_name="Hisse-Robotu-VBTS-Denetim-Gunlugu.csv",
                    mime="text/csv; charset=utf-8",
                    width="stretch",
                    key="vbts_denetim_csv_indir",
                )

            st.markdown("**Yedek bakım politikası**")
            keep_latest = st.number_input(
                "Saklanacak en yeni yedek sayısı",
                min_value=1,
                max_value=100,
                value=20,
                step=1,
                key="vbts_yedek_saklama_sayisi",
            )
            prune_confirmed = st.checkbox(
                "Belirlenen sınırı aşan eski VBTS yedeklerinin "
                "kalıcı olarak silinmesini onaylıyorum.",
                value=False,
                key="vbts_yedek_temizleme_onayi",
            )
            prune_requested = st.button(
                "Eski VBTS yedeklerini temizle",
                width="stretch",
                disabled=not prune_confirmed,
                key="vbts_yedek_temizle",
            )
            if prune_requested:
                try:
                    removed = prune_vbts_backups(
                        csv_path,
                        keep_latest=int(keep_latest),
                    )
                except DashboardVbtsManagerError as hata:
                    tarama_hazir = False
                    st.error(str(hata))
                else:
                    st.session_state["vbts_yonetim_bildirimi"] = (
                        f"{len(removed)} eski VBTS yedeği temizlendi."
                    )
                    st.rerun()


        st.markdown("**Yeni VBTS kaydı ekle**")
        with st.form("vbts_kaydi_ekle_formu", clear_on_submit=True):
            sol, sag = st.columns(2)
            with sol:
                sembol = st.text_input("Hisse sembolü", value="")
                tedbir_turu = st.text_input("VBTS tedbir türü", value="")
                baslangic = st.date_input(
                    "Başlangıç tarihi",
                    value=date.today(),
                    key="vbts_baslangic_tarihi",
                )
            with sag:
                bitis = st.date_input(
                    "Bitiş tarihi",
                    value=date.today() + timedelta(days=30),
                    key="vbts_bitis_tarihi",
                )
                kap_referansi = st.text_input(
                    "Resmî KAP bildirim referansı",
                    value="",
                )
                resmi_onay = st.checkbox(
                    "Resmî KAP bildirimiyle doğruladım.",
                    value=False,
                )

            ekle = st.form_submit_button(
                "VBTS kaydını ekle",
                type="primary",
                width="stretch",
            )

        if ekle:
            if not resmi_onay:
                st.error(
                    "VBTS kaydı eklemek için resmî KAP bildirimiyle "
                    "doğrulama onayı verilmelidir."
                )
                return tarama_hazir

            try:
                record = build_vbts_record(
                    symbol=sembol,
                    measure_type=tedbir_turu,
                    start_date=baslangic,
                    end_date=bitis,
                    source_reference=kap_referansi,
                )
                updated = add_vbts_record(csv_path, record)
            except DashboardVbtsManagerError as hata:
                tarama_hazir = False
                st.error(str(hata))
            else:
                st.session_state["vbts_yonetim_bildirimi"] = (
                    f"{record.symbol.removesuffix('.IS')} VBTS kaydı eklendi. "
                    f"Toplam arşiv kaydı: {len(updated)}"
                )
                st.rerun()

        if records:
            st.divider()
            record_map = {
                (
                    f"{record.symbol.removesuffix('.IS')} · "
                    f"{record.status()} · {record.measure_type} · "
                    f"{record.source_reference}"
                ): record
                for record in records
            }
            selected_label = st.selectbox(
                "Silinecek VBTS kaydı",
                options=tuple(record_map),
                key="vbts_silinecek_kayit",
            )
            delete_confirmed = st.checkbox(
                "Seçili kaydın arşivden kalıcı olarak kaldırılmasını onaylıyorum.",
                value=False,
                key="vbts_silme_onayi",
            )
            delete_requested = st.button(
                "Seçili VBTS kaydını sil",
                width="stretch",
                disabled=not delete_confirmed,
                key="vbts_kaydi_sil",
            )

            if delete_requested:
                selected = record_map[selected_label]
                try:
                    remaining = delete_vbts_record(
                        csv_path,
                        selected.record_key,
                    )
                except DashboardVbtsManagerError as hata:
                    tarama_hazir = False
                    st.error(str(hata))
                else:
                    st.session_state["vbts_yonetim_bildirimi"] = (
                        "VBTS kaydı silindi. "
                        f"Kalan arşiv kaydı: {len(remaining)}"
                    )
                    st.rerun()

    return tarama_hazir


def manuel_vbts_durum_paneli_goster() -> None:
    """Manuel VBTS CSV kaynağının özet durumunu tekrar üretmeden gösterir."""

    csv_path_raw = os.getenv("HISSE_ROBOTU_VBTS_CSV_PATH", "").strip()

    if not csv_path_raw:
        st.info("VBTS CSV durumu: Dosya yolu tanımlı değil")
        return

    csv_path = Path(csv_path_raw)

    if not csv_path.exists():
        st.info("VBTS CSV durumu: Dosya bulunamadı")
        st.caption(f"Beklenen konum: {csv_path}")
        return

    try:
        dataset = load_dashboard_vbts_dataset()
    except DashboardManualVbtsError:
        st.info("VBTS CSV durumu: Dosya doğrulanamadı")
        st.caption(f"Beklenen konum: {csv_path}")
        return

    modified_at = datetime.fromtimestamp(
        csv_path.stat().st_mtime,
        tz=timezone.utc,
    ).astimezone()

    st.caption(f"VBTS CSV dosyası: {csv_path}")
    st.caption(
        "Son güncelleme: "
        + modified_at.strftime("%Y-%m-%d %H:%M:%S")
    )
    st.caption(f"Kayıt sayısı: {len(dataset.measures)}")

def kap_vbts_durum_karti_goster() -> bool:
    """Seçilen VBTS veri kaynağının kullanılabilirlik durumunu gösterir."""

    source_name = os.getenv("HISSE_ROBOTU_VBTS_SOURCE", "").strip().lower()

    if not source_name:
        st.error("VBTS veri kaynağı seçilmedi — Toplu tarama kilitli.")
        st.caption(
            "HISSE_ROBOTU_VBTS_SOURCE ortam değişkeni tanımlanmalıdır. "
            "Desteklenen kaynak: manual_csv."
        )
        return False

    if source_name == "manual_csv":
        csv_path_raw = os.getenv("HISSE_ROBOTU_VBTS_CSV_PATH", "").strip()

        if not csv_path_raw:
            st.error(
                "Manuel VBTS kaynağı seçildi — CSV dosyası tanımlı değil."
            )
            st.caption(
                "HISSE_ROBOTU_VBTS_CSV_PATH ortam değişkeni "
                "güncel ve doğrulanmış dosyayı göstermelidir."
            )
            return False

        try:
            load_dashboard_vbts_dataset()
        except DashboardManualVbtsError as exc:
            st.error("Manuel VBTS kaynağı kullanılamıyor — Toplu tarama kilitli.")
            st.caption(str(exc))
            return False

        st.success("Manuel VBTS koruması aktif.")
        st.caption(
            "Toplu tarama güncel ve doğrulanmış manuel VBTS CSV "
            "filtresiyle çalışacaktır."
        )
        return True

    st.error(f"VBTS veri kaynağı desteklenmiyor: {source_name}")
    st.caption("Toplu tarama kilitli.")
    return False

def temel_skor_deposu() -> FundamentalScoreJsonStore:
    return FundamentalScoreJsonStore(
        Path("backend/data/fundamental_scores.json")
    )


def kayitli_temel_skorlari_yukle() -> dict:
    try:
        return temel_skor_deposu().load_latest_scores()
    except FundamentalScoreStoreError as hata:
        st.warning(f"Kayıtlı temel skorlar okunamadı: {hata}")
        return {}


def bist_toplu_tarama_sonucu_goster(
    sonuc: MarketScanResult,
    *,
    temel_skorlar: dict | None = None,
    temel_filtre_aktif: bool = False,
    minimum_temel_skor: int = 60,
) -> None:
    if not veri_tazeligi_kilidi_goster(sonuc.veri_tazeligi):
        return
    st.subheader(f"{sonuc.evren_adi} güncel aday taraması")
    metrik_izgarasi_goster(
        (
            ("Tarama evreni", str(sonuc.evren_sembol_sayisi)),
            ("Başarılı analiz", str(sonuc.filtrelenmis.aday_sayisi + sonuc.filtrelenmis.elenen_sayisi)),
            ("Filtreyi geçen", str(sonuc.filtrelenmis.aday_sayisi)),
            ("Gösterilen aday", str(sonuc.gosterilen_aday_sayisi)),
            ("Elenen", str(sonuc.filtrelenmis.elenen_sayisi)),
            ("Veri hatası", str(sonuc.filtrelenmis.hatali_sayisi)),
        )
    )
    st.caption(
        f"Evren kaynağı: {sonuc.evren_kaynagi} · "
        f"Bileşen tarihi: {sonuc.evren_tarihi} · "
        f"Profil: {sonuc.profil.ad}"
    )
    st.info(
        "Sonuçlar kesin alım tavsiyesi değildir. Tablo, ayrıntılı güncel "
        "teknik analizde doğrulanacak araştırma adaylarını sıralar."
    )

    adaylar = sonuc.adaylar
    temel_filtre_sonucu = apply_optional_fundamental_filter(
        adaylar,
        symbol_getter=lambda aday: aday.sembol,
        scores=temel_skorlar or {},
        enabled=temel_filtre_aktif,
        minimum_score=minimum_temel_skor,
    )
    gorunen_semboller = {
        aday.sembol for aday in temel_filtre_sonucu.accepted
    }
    kayitlar = [
        kayit
        for aday, kayit in zip(
            sonuc.adaylar,
            aday_tablosu_kayitlari(sonuc),
        )
        if aday.sembol in gorunen_semboller
    ]

    for aday, kayit in zip(
        (
            aday
            for aday in sonuc.adaylar
            if aday.sembol in gorunen_semboller
        ),
        kayitlar,
    ):
        sembol = aday.sembol.removesuffix(".IS").upper()
        temel_skor = (temel_skorlar or {}).get(sembol)
        kayit["Temel skor"] = (
            temel_skor.total_score
            if temel_skor is not None
            and not temel_skor.locked
            else None
        )

    if temel_filtre_aktif:
        st.info(
            f"İsteğe bağlı temel analiz filtresi aktif: "
            f"minimum {minimum_temel_skor}/100 · "
            f"geçen {len(temel_filtre_sonucu.accepted)} · "
            f"elenen {len(temel_filtre_sonucu.rejected)} · "
            f"verisi eksik {len(temel_filtre_sonucu.missing)}."
        )

    if not kayitlar:
        st.warning(
            "Seçili profil koşullarını karşılayan aday bulunamadı. "
            "Daha geniş bir evren veya daha gevşek profil denenebilir."
        )
    else:
        st.dataframe(
            pd.DataFrame(kayitlar),
            width="stretch",
            hide_index=True,
            column_config={
                "Sıra": st.column_config.NumberColumn(width="small"),
                "Hisse": st.column_config.TextColumn(width="small"),
                "Skor": st.column_config.NumberColumn(width="small"),
                "Temel skor": st.column_config.NumberColumn(
                    width="small",
                    format="%d",
                ),
                "Durum": st.column_config.TextColumn(width="medium"),
                "Son kapanış": st.column_config.NumberColumn(format="%.2f"),
                "Giriş": st.column_config.NumberColumn(format="%.2f"),
                "Stop": st.column_config.NumberColumn(format="%.2f"),
                "Hedef": st.column_config.NumberColumn(format="%.2f"),
                "Risk/Getiri": st.column_config.NumberColumn(format="1:%.2f"),
                "Hacim oranı": st.column_config.NumberColumn(format="%.2fx"),
                "RSI14": st.column_config.NumberColumn(format="%.2f"),
                "ATR (%)": st.column_config.NumberColumn(format="%.2f%%"),
            },
        )

        secili = st.selectbox(
            "Aday ayrıntısı",
            options=temel_filtre_sonucu.accepted,
            format_func=lambda aday: (
                f"{aday.sembol.removesuffix('.IS')} · "
                f"{aday.sinyal.skor}/100 · {aday.sinyal.karar}"
            ),
            key="bist_toplu_tarama_aday_ayrintisi",
        )
        sol, sag = st.columns(2)
        with sol:
            aciklama_listesi_goster(
                "Olumlu gerekçeler",
                secili.sinyal.pozitif_nedenler,
                "Belirgin olumlu gerekçe yok.",
            )
        with sag:
            aciklama_listesi_goster(
                "Riskler",
                secili.sinyal.riskler,
                "Belirgin risk yok.",
            )

    if sonuc.filtrelenmis.elenenler:
        with st.expander("Elenen hisseler ve nedenleri", expanded=False):
            elenen_kayitlari = []
            for elenen in sonuc.filtrelenmis.elenenler:
                elenen_kayitlari.append(
                    {
                        "Hisse": elenen.sembol.removesuffix(".IS"),
                        "Neden": " | ".join(elenen.nedenler),
                    }
                )
            st.dataframe(
                pd.DataFrame(elenen_kayitlari),
                width="stretch",
                hide_index=True,
            )

    if sonuc.filtrelenmis.hatalar:
        with st.expander("Verisi alınamayan hisseler", expanded=False):
            st.dataframe(
                pd.DataFrame(
                    {
                        "Hisse": hata.sembol.removesuffix(".IS"),
                        "Hata": hata.hata,
                    }
                    for hata in sonuc.filtrelenmis.hatalar
                ),
                width="stretch",
                hide_index=True,
            )


def bist_toplu_tarama_formu() -> None:
    bildirim = st.session_state.pop("vbts_yonetim_bildirimi", None)
    if bildirim:
        st.success(bildirim)

    vbts_operasyonel_hazir = vbts_yonetim_paneli_goster()
    kap_vbts_durum_karti_goster()
    manuel_vbts_durum_paneli_goster()

    hazir_tarama_servisi: BistMarketScannerService | None = None
    vbts_hazirlik_hatasi: str | None = None
    if vbts_operasyonel_hazir:
        try:
            hazir_tarama_servisi = build_dashboard_market_scanner()
        except DashboardMarketScannerSourceError as hata:
            vbts_hazirlik_hatasi = str(hata)

    vbts_tarama_hazir = (
        vbts_operasyonel_hazir and hazir_tarama_servisi is not None
    )
    if not vbts_tarama_hazir:
        st.error(
            "VBTS koruması hazır değil — toplu tarama güvenlik nedeniyle kilitli."
        )
        if vbts_hazirlik_hatasi:
            st.caption(vbts_hazirlik_hatasi)

    with st.sidebar:
        st.header("BIST toplu tarama")
        st.caption(
            "Seçilen evrendeki hisseleri günlük teknik skor, hacim ve "
            "risk/getiri koşullarıyla topluca sıralar."
        )
        with st.form("bist_toplu_tarama_formu"):
            evren = st.selectbox(
                "Tarama evreni",
                options=TARAMA_EVRENLERI,
                index=0,
            )
            ozel_liste = st.text_area(
                "Özel hisse listesi",
                value="THYAO, ASELS, TUPRS, SAHOL, KCHOL",
                height=90,
                help=(
                    "Virgül, boşluk veya yeni satırla ayırabilirsiniz. "
                    "Bu alan yalnızca Özel Liste evreninde kullanılır."
                ),
            )
            profil_etiketi = st.selectbox(
                "Tarama profili",
                options=tuple(TARAMA_PROFILLERI),
                index=1,
                help=(
                    "Dengeli profil skor, hacim, risk/getiri ve "
                    "pozitif/nötr görünümü birlikte uygular."
                ),
            )
            maksimum_aday = st.slider(
                "Gösterilecek aday sayısı",
                min_value=1,
                max_value=50,
                value=15,
            )
            internetten_guncelle = st.checkbox(
                "BIST evrenini resmi kaynaktan güncelle",
                value=True,
                disabled=(evren not in ("BIST 30", "BIST 100", "BIST 500", "BIST Tüm")),
            )
            temel_filtre_aktif = st.checkbox(
                "Temel kalite filtresini kullan",
                value=False,
                help=(
                    "Varsayılan olarak kapalıdır. Açıldığında önce "
                    "kayıtlı ve güncel temel kalite skorları kullanılır."
                ),
            )
            minimum_temel_skor = st.slider(
                "Minimum temel kalite skoru",
                min_value=0,
                max_value=100,
                value=60,
                disabled=not temel_filtre_aktif,
            )
            temel_filtre_dosyasi = st.file_uploader(
                "Temel skorları güncellemek için bilanço dosyası",
                type=("csv", "json"),
                disabled=not temel_filtre_aktif,
                key="bist_temel_filtre_dosyasi",
                help=(
                    "İsteğe bağlıdır. Dosya yüklenmezse yerel depodaki "
                    "güncel temel kalite skorları kullanılır."
                ),
            )
            calistirildi = st.form_submit_button(
                "Toplu taramayı başlat",
                type="primary",
                width="stretch",
                disabled=not vbts_tarama_hazir,
            )

    if not calistirildi:
        st.info(
            "Tarama evrenini ve profili seçip sol menüdeki "
            "‘Toplu taramayı başlat’ düğmesine basın."
        )
        st.caption(
            "BIST Tüm seçeneği yüzlerce hisse içerdiğinden diğer "
            "evrenlere göre daha uzun sürebilir."
        )
        return

    if not vbts_tarama_hazir or hazir_tarama_servisi is None:
        st.error(
            "VBTS koruması doğrulanamadığı için toplu tarama başlatılmadı."
        )
        return

    temel_skorlar: dict = {}
    if temel_filtre_aktif:
        temel_skorlar = kayitli_temel_skorlari_yukle()

        if temel_filtre_dosyasi is not None:
            try:
                temel_icerik = temel_filtre_dosyasi.getvalue()
                if (
                    Path(temel_filtre_dosyasi.name).suffix.lower()
                    == ".csv"
                ):
                    temel_donemler = periods_from_csv_bytes(
                        temel_icerik
                    )
                else:
                    temel_donemler = periods_from_json_bytes(
                        temel_icerik
                    )

                for temel_sembol in sorted(
                    {item.symbol for item in temel_donemler}
                ):
                    sembol_donemleri = [
                        item
                        for item in temel_donemler
                        if item.symbol == temel_sembol
                    ]
                    sembol_tazeligi = (
                        evaluate_fundamental_freshness(
                            sembol_donemleri
                        )
                    )
                    if sembol_tazeligi.locked:
                        continue

                    sembol_snapshot = build_fundamental_snapshot(
                        sembol_donemleri
                    )
                    skor = calculate_fundamental_quality(
                        sembol_snapshot,
                        sembol_tazeligi,
                    )
                    if skor.locked or skor.total_score is None:
                        continue

                    temel_skor_deposu().save(
                        periods=sembol_donemleri,
                        score=skor,
                    )
                    temel_skorlar[temel_sembol] = skor
            except (
                FundamentalDataError,
                FundamentalScoreStoreError,
                ValueError,
                TypeError,
                UnicodeError,
            ) as hata:
                st.error(
                    f"Temel filtre dosyası doğrulanamadı: {hata}"
                )
                return

        if not temel_skorlar:
            st.error(
                "Temel kalite filtresi için güncel kayıtlı skor "
                "bulunamadı. Temel Analiz ekranında bilanço dosyası "
                "yükleyerek skorları kaydedin."
            )
            return

    ilerleme = st.progress(0, text="Tarama hazırlanıyor...")
    durum = st.empty()

    def ilerleme_bildir(sira: int, toplam: int, sembol: str) -> None:
        oran = min(max(sira / toplam, 0.0), 1.0)
        ilerleme.progress(
            oran,
            text=f"[{sira}/{toplam}] {sembol} analiz ediliyor...",
        )
        durum.caption(f"Son işlenen hisse: {sembol}")

    try:
        istek = MarketScanRequest(
            evren=evren,
            profil_adi=TARAMA_PROFILLERI[profil_etiketi],
            maksimum_aday=int(maksimum_aday),
            ozel_semboller=ozel_sembol_metinini_ayristir(ozel_liste),
            internetten_evren_guncelle=bool(internetten_guncelle),
        )
        with st.spinner(f"{istek.evren} güncel verilerle taranıyor..."):
            tarama_servisi = hazir_tarama_servisi
            sonuc = tarama_servisi.calistir(
                istek,
                ilerleme_bildirimi=ilerleme_bildir,
            )
    except (
        ValueError,
        TypeError,
        MarketScannerError,
        DashboardMarketScannerSourceError,
    ) as hata:
        ilerleme.empty()
        durum.empty()
        st.error(str(hata))
        return

    ilerleme.progress(1.0, text="Toplu tarama tamamlandı.")
    durum.empty()
    bist_toplu_tarama_sonucu_goster(
        sonuc,
        temel_skorlar=temel_skorlar,
        temel_filtre_aktif=bool(temel_filtre_aktif),
        minimum_temel_skor=int(minimum_temel_skor),
    )


def acik_pozisyon_sonucu_goster(sonuc: PositionMonitoringResult) -> None:
    st.subheader(f"{sonuc.sembol} açık pozisyon izleme")
    metrik_izgarasi_goster(
        (
            ("Pozisyon durumu", sonuc.durum),
            ("Önerilen eylem", sonuc.eylem),
            ("Son kapanış", para_yaz(sonuc.son_kapanis)),
            ("Açık kâr/zarar", para_yaz(sonuc.acik_kar_zarar)),
            ("Getiri", yuzde_yaz(sonuc.acik_kar_zarar_yuzde)),
            ("Gerçekleşmemiş R", f"{sonuc.r_katsayisi:.2f}R"),
            ("Dinamik stop", para_yaz(sonuc.dinamik_stop)),
            ("Stop mesafesi", f"{para_yaz(sonuc.stop_mesafesi)} · %{sonuc.stop_mesafesi_yuzde:.2f}"),
        )
    )

    st.markdown("**Stop ve kâr koruma**")
    st.dataframe(
        pd.DataFrame(
            (
                {"Alan": "İlk stop", "Değer": sonuc.ilk_stop},
                {"Alan": "Önceki stop", "Değer": sonuc.onceki_stop},
                {"Alan": "Dinamik stop", "Değer": sonuc.dinamik_stop},
                {"Alan": "Pozisyon içi zirve", "Değer": sonuc.en_yuksek_fiyat},
                {"Alan": "En yüksek kapanış", "Değer": sonuc.en_yuksek_kapanis},
            )
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption(f"Dinamik stop kaynağı: {sonuc.stop_kaynagi}")

    kar_alma = (
        "Tam çıkış"
        if sonuc.hedef_2.durum == "Ulaşıldı"
        else (
            f"{sonuc.onerilen_kismi_kar_lotu} lot kısmi kâr"
            if sonuc.kismi_kar_onerisi
            else "Yok"
        )
    )
    st.markdown("**Hedef ilerlemesi**")
    st.dataframe(
        pd.DataFrame(
            (
                {
                    "Hedef": "Hedef 1",
                    "Fiyat": sonuc.hedef_1.hedef,
                    "Durum": sonuc.hedef_1.durum,
                    "Kalan (%)": round(sonuc.hedef_1.kalan_yuzde, 2),
                },
                {
                    "Hedef": "Hedef 2",
                    "Fiyat": sonuc.hedef_2.hedef,
                    "Durum": sonuc.hedef_2.durum,
                    "Kalan (%)": round(sonuc.hedef_2.kalan_yuzde, 2),
                },
            )
        ),
        width="stretch",
        hide_index=True,
    )
    st.info(f"Kâr alma değerlendirmesi: {kar_alma}")

    aciklama_listesi_goster(
        "Pozitif unsurlar",
        sonuc.pozitif_nedenler,
        "Belirgin pozitif unsur yok.",
    )
    aciklama_listesi_goster(
        "Riskler",
        sonuc.riskler,
        "Belirgin yeni risk yok.",
    )
    aciklama_listesi_goster(
        "Notlar",
        sonuc.notlar,
        "Ek not yok.",
    )

    with st.expander("İzleme kimlikleri", expanded=False):
        st.code(
            "\n".join(
                (
                    f"Veri kimliği: {sonuc.veri_kimligi}",
                    f"Teknik analiz kimliği: {sonuc.teknik_analiz_kimligi}",
                    f"İzleme kimliği: {sonuc.izleme_kimligi}",
                )
            )
        )


def acik_pozisyon_izleme_formu() -> None:
    with st.sidebar:
        st.header("Açık pozisyon ayarları")
        with st.form("acik_pozisyon_izleme_formu"):
            sembol = st.text_input(
                "Hisse sembolü",
                value="THYAO",
                help="BIST uzantısı yazılmazsa .IS otomatik eklenir.",
            )
            giris_tarihi = st.date_input(
                "Giriş tarihi",
                value=datetime.now().date().replace(day=1),
            )
            giris_fiyati = st.number_input(
                "Giriş fiyatı",
                min_value=0.01,
                value=300.0,
                step=0.25,
            )
            lot_sayisi = st.number_input(
                "Açık lot",
                min_value=1,
                value=100,
                step=1,
            )
            ilk_stop = st.number_input(
                "İlk stop",
                min_value=0.01,
                value=286.50,
                step=0.25,
            )
            hedef_1 = st.number_input(
                "Hedef 1",
                min_value=0.01,
                value=327.0,
                step=0.25,
            )
            hedef_2 = st.number_input(
                "Hedef 2",
                min_value=0.01,
                value=354.0,
                step=0.25,
            )
            mevcut_stop_kullan = st.checkbox("Yükseltilmiş mevcut stop var")
            mevcut_stop_degeri = st.number_input(
                "Mevcut stop",
                min_value=0.01,
                value=286.50,
                step=0.25,
                disabled=not mevcut_stop_kullan,
            )
            hedef_1_gerceklesti = st.checkbox(
                "Hedef 1 için daha önce kısmi kâr alındı"
            )
            calistirildi = st.form_submit_button(
                "Pozisyonu güncelle",
                type="primary",
                width="stretch",
            )

    if not calistirildi:
        st.info(
            "Açık pozisyon bilgilerini girip sol menüdeki "
            "‘Pozisyonu güncelle’ düğmesine basın."
        )
        return

    try:
        istek = OpenPositionDashboardRequest(
            sembol=sembol,
            giris_tarihi=giris_tarihi,
            giris_fiyati=float(giris_fiyati),
            lot_sayisi=int(lot_sayisi),
            ilk_stop=float(ilk_stop),
            hedef_1=float(hedef_1),
            hedef_2=float(hedef_2),
            mevcut_stop=(
                float(mevcut_stop_degeri) if mevcut_stop_kullan else None
            ),
            hedef_1_gerceklesti=bool(hedef_1_gerceklesti),
        )
        with st.spinner(f"{istek.sembol} açık pozisyonu güncelleniyor..."):
            sonuc = OpenPositionDashboardService().calistir(istek)
    except (ValueError, TypeError, LiveAnalysisDashboardError) as hata:
        st.error(str(hata))
        return

    acik_pozisyon_sonucu_goster(sonuc)

def tek_hisse_formu() -> None:
    with st.sidebar:
        st.header("Tek hisse ayarları")

        with st.form("tek_hisse_backtest_formu"):
            sembol = st.text_input(
                "Hisse sembolü",
                value="THYAO",
                help="BIST uzantısı yazılmazsa .IS otomatik eklenir.",
            )
            indirme_donemi = st.selectbox(
                "Veri dönemi",
                options=("1y", "2y", "5y", "10y", "max"),
                index=2,
            )
            islem_gunu = st.number_input(
                "En fazla işlem günü",
                min_value=100,
                max_value=10_000,
                value=1253,
                step=50,
            )
            gorunum_etiketi = st.selectbox(
                "Teknik görünüm",
                options=tuple(GORUNUM_SECENEKLERI),
                index=0,
            )
            minimum_skor = st.slider(
                "Minimum sinyal skoru",
                min_value=0,
                max_value=100,
                value=50,
            )
            elde_tutma_gunu = st.slider(
                "Elde tutma süresi (bar)",
                min_value=1,
                max_value=30,
                value=10,
            )
            baslangic_sermayesi = st.number_input(
                "Başlangıç sermayesi",
                min_value=1_000.0,
                value=100_000.0,
                step=10_000.0,
            )
            pozisyon_yuzde = st.slider(
                "Pozisyon sermayesi (%)",
                min_value=1.0,
                max_value=100.0,
                value=100.0,
                step=1.0,
            )
            maliyet_yuzde = st.number_input(
                "İşlem maliyeti (%)",
                min_value=0.0,
                max_value=9.99,
                value=0.10,
                step=0.01,
            )
            stop_yuzde = st.number_input(
                "Zarar durdur (%)",
                min_value=0.01,
                max_value=99.0,
                value=5.0,
                step=0.5,
            )
            hedef_yuzde = st.number_input(
                "Hedef (%)",
                min_value=0.01,
                max_value=99.0,
                value=10.0,
                step=0.5,
            )

            calistirildi = st.form_submit_button(
                "Backtest'i başlat",
                type="primary",
                width="stretch",
            )

    if not calistirildi:
        st.info(
            "Ayarları seçip sol menüdeki "
            "‘Backtest'i başlat’ düğmesine basın."
        )
        return

    try:
        istek = DashboardBacktestRequest(
            sembol=sembol,
            islem_gunu=int(islem_gunu),
            indirme_donemi=indirme_donemi,
            gorunum_secimi=GORUNUM_SECENEKLERI[gorunum_etiketi],
            elde_tutma_gunu=int(elde_tutma_gunu),
            minimum_skor=int(minimum_skor),
            baslangic_sermayesi=float(baslangic_sermayesi),
            pozisyon_yuzde=float(pozisyon_yuzde),
            maliyet_yuzde=float(maliyet_yuzde),
            stop_yuzde=float(stop_yuzde),
            hedef_yuzde=float(hedef_yuzde),
        )

        with st.spinner(
            f"{istek.sembol} verisi hazırlanıyor ve backtest çalışıyor..."
        ):
            sonuc = BacktestDashboardService().calistir(istek)

    except (ValueError, TypeError, BacktestServiceError) as hata:
        st.error(str(hata))
        return

    kayit = gecmise_kaydet(sonuc)
    if kayit is not None:
        st.caption("Analiz geçmişine kaydedildi.")
    tek_hisse_sonucu_goster(sonuc)


def portfoy_formu() -> None:
    with st.sidebar:
        st.header("Portföy ayarları")

        with st.form("portfoy_backtest_formu"):
            semboller = st.text_area(
                "Hisse sembolleri",
                value="THYAO, TUPRS, ASELS",
                help=(
                    "Sembolleri virgül, boşluk veya yeni satırla ayırın. "
                    "En fazla 10 hisse kullanılabilir."
                ),
                height=90,
            )
            maksimum_pozisyon = st.number_input(
                "Maksimum eş zamanlı pozisyon",
                min_value=1,
                max_value=10,
                value=3,
                step=1,
            )
            indirme_donemi = st.selectbox(
                "Veri dönemi",
                options=("1y", "2y", "5y", "10y", "max"),
                index=2,
            )
            islem_gunu = st.number_input(
                "En fazla işlem günü",
                min_value=100,
                max_value=10_000,
                value=1253,
                step=50,
            )
            gorunum_etiketi = st.selectbox(
                "Teknik görünüm",
                options=tuple(GORUNUM_SECENEKLERI),
                index=0,
            )
            minimum_skor = st.slider(
                "Minimum sinyal skoru",
                min_value=0,
                max_value=100,
                value=50,
            )
            elde_tutma_gunu = st.slider(
                "Elde tutma süresi (bar)",
                min_value=1,
                max_value=30,
                value=10,
            )
            baslangic_sermayesi = st.number_input(
                "Başlangıç sermayesi",
                min_value=1_000.0,
                value=100_000.0,
                step=10_000.0,
            )
            maliyet_yuzde = st.number_input(
                "İşlem maliyeti (%)",
                min_value=0.0,
                max_value=9.99,
                value=0.10,
                step=0.01,
            )
            stop_yuzde = st.number_input(
                "Zarar durdur (%)",
                min_value=0.01,
                max_value=99.0,
                value=5.0,
                step=0.5,
            )
            hedef_yuzde = st.number_input(
                "Hedef (%)",
                min_value=0.01,
                max_value=99.0,
                value=10.0,
                step=0.5,
            )

            calistirildi = st.form_submit_button(
                "Portföy backtest'ini başlat",
                type="primary",
                width="stretch",
            )

    if not calistirildi:
        st.info(
            "Hisseleri ve ayarları seçip sol menüdeki "
            "‘Portföy backtest'ini başlat’ düğmesine basın."
        )
        return

    try:
        istek = PortfolioDashboardRequest(
            semboller=semboller,
            islem_gunu=int(islem_gunu),
            indirme_donemi=indirme_donemi,
            gorunum_secimi=GORUNUM_SECENEKLERI[gorunum_etiketi],
            elde_tutma_gunu=int(elde_tutma_gunu),
            minimum_skor=int(minimum_skor),
            baslangic_sermayesi=float(baslangic_sermayesi),
            maliyet_yuzde=float(maliyet_yuzde),
            stop_yuzde=float(stop_yuzde),
            hedef_yuzde=float(hedef_yuzde),
            maksimum_es_zamanli_pozisyon=int(maksimum_pozisyon),
        )

        with st.spinner(
            f"{len(istek.semboller)} hisse hazırlanıyor ve "
            "portföy backtest’i çalışıyor..."
        ):
            sonuc = PortfolioDashboardService().calistir(istek)

    except (ValueError, TypeError, PortfolioDashboardError) as hata:
        st.error(str(hata))
        return

    kayit = gecmise_kaydet(sonuc)
    if kayit is not None:
        st.caption("Analiz geçmişine kaydedildi.")
    portfoy_sonucu_goster(sonuc)




def _opsiyonel_fiyat(deger: float) -> float | None:
    return float(deger) if float(deger) > 0 else None


def _islem_kaydi_etiketi(kayit: TradeRecord) -> str:
    return (
        f"{kayit.exit_date.isoformat()} · {kayit.symbol.removesuffix('.IS')} · "
        f"{para_yaz(kayit.net_pnl)} · {kayit.record_id}"
    )


def _kayip_ozeti_goster(
    sonuc: LossAnalysisResult,
    kayitlar: tuple[TradeRecord, ...],
    depo: TradeJournalStore,
) -> None:
    ozet = sonuc.summary
    kar_faktoru = "—" if ozet.profit_factor is None else f"{ozet.profit_factor:.2f}"
    metrik_izgarasi_goster(
        (
            ("Toplam işlem", str(ozet.trade_count)),
            ("Kazanan / Kaybeden", f"{ozet.winning_count} / {ozet.losing_count}"),
            ("Net K/Z", para_yaz(ozet.net_pnl)),
            ("Başarı oranı", yuzde_yaz(ozet.win_rate_pct)),
            ("Kâr faktörü", kar_faktoru),
            ("İşlem başına beklenti", para_yaz(ozet.expectancy)),
            ("Azami düşüş", para_yaz(ozet.max_drawdown)),
            ("Azami düşüş %", yuzde_yaz(ozet.max_drawdown_pct)),
            ("En uzun zarar serisi", str(ozet.max_consecutive_losses)),
        )
    )
    st.caption(
        f"Güvenlik değerlendirme tarihi: {sonuc.evaluation_date.isoformat()} · "
        f"Günlük net sonuç: {para_yaz(sonuc.safety_context.daily_net_pnl)} · "
        f"Haftalık net sonuç: {para_yaz(sonuc.safety_context.weekly_net_pnl)} · "
        f"Güncel ardışık zarar: {sonuc.safety_context.consecutive_losses}"
    )

    if sonuc.causes:
        st.subheader("Kayıp nedenleri")
        st.info(
            "Neden dağılımı, günlükte kayıtlı stop/hedef ve kullanıcı işaretlerine "
            "dayanır. Bir zararın birden fazla nedeni olabilir; zarar tutarı nedenler "
            "arasında eşit paylaştırılarak yalnızca teşhis amacıyla gösterilir."
        )
        st.dataframe(
            pd.DataFrame(cause_table(sonuc)),
            width="stretch",
            hide_index=True,
        )
        st.subheader("Zarar eden işlemler")
        st.dataframe(
            pd.DataFrame(diagnostic_table(sonuc)),
            width="stretch",
            hide_index=True,
        )
    else:
        st.success("Seçilen kayıtlarda zarar eden tamamlanmış işlem bulunmuyor.")

    st.subheader("İşlem günlüğü")
    st.dataframe(
        pd.DataFrame(journal_table(kayitlar)),
        width="stretch",
        hide_index=True,
    )

    if kayitlar:
        with st.expander("Yanlış kaydı sil", expanded=False):
            secenekler = {_islem_kaydi_etiketi(item): item.record_id for item in kayitlar}
            secilen = st.selectbox("Silinecek kayıt", options=tuple(secenekler))
            if st.button("Seçilen kaydı sil", type="secondary", width="stretch"):
                try:
                    if depo.delete(secenekler[secilen]):
                        st.session_state["islem_gunlugu_bildirimi"] = "İşlem kaydı silindi."
                        st.rerun()
                except TradeJournalError as hata:
                    st.error(str(hata))


def _islem_kaydi_ekle(depo: TradeJournalStore) -> None:
    st.subheader("Tamamlanmış işlem ekle")
    st.caption(
        "Buraya yalnızca gerçekleşmiş değerleri girin. Stop ve hedef kullanılmadıysa "
        "ilgili alana 0 yazın. Gerçek ve deneme hesapları ayrı tutulur."
    )
    with st.form("islem_kaydi_ekle_formu"):
        sol, orta, sag = st.columns(3)
        with sol:
            hesap = st.selectbox("Hesap türü", options=HESAP_TURLERI)
            sembol = st.text_input("Hisse sembolü", value="THYAO")
            giris_tarihi = st.date_input(
                "Giriş tarihi",
                value=datetime.now().date() - timedelta(days=7),
                key="gunluk_giris_tarihi",
            )
            cikis_tarihi = st.date_input(
                "Çıkış tarihi",
                value=datetime.now().date(),
                key="gunluk_cikis_tarihi",
            )
        with orta:
            giris_fiyati = st.number_input(
                "Giriş fiyatı", min_value=0.01, value=100.0, step=0.25
            )
            cikis_fiyati = st.number_input(
                "Çıkış fiyatı", min_value=0.01, value=100.0, step=0.25
            )
            lot = st.number_input("Lot", min_value=1, value=100, step=1)
            sermaye = st.number_input(
                "İşlem anındaki sermaye",
                min_value=1_000.0,
                value=100_000.0,
                step=10_000.0,
            )
        with sag:
            stop = st.number_input(
                "Planlanan stop (0 = yok)", min_value=0.0, value=0.0, step=0.25
            )
            hedef = st.number_input(
                "Planlanan hedef (0 = yok)", min_value=0.0, value=0.0, step=0.25
            )
            masraf = st.number_input(
                "Toplam komisyon/masraf", min_value=0.0, value=0.0, step=1.0
            )
            sinyal = st.text_input("Sinyal sınıfı", value="")

        gec_giris = st.checkbox("Girişin geç yapıldığını düşünüyorum")
        kaybedene_ekleme = st.checkbox("Kaybeden pozisyona ekleme yapıldı")
        asiri_yukselmis = st.checkbox("Aşırı yükselmiş bölgede giriş yapıldı")
        notlar = st.text_area("Notlar", value="", height=80)
        kaydet = st.form_submit_button(
            "İşlemi günlüğe kaydet", type="primary", width="stretch"
        )

    if not kaydet:
        return
    try:
        kayit = TradeRecord(
            account_type=hesap,
            symbol=sembol,
            entry_date=giris_tarihi,
            exit_date=cikis_tarihi,
            entry_price=float(giris_fiyati),
            exit_price=float(cikis_fiyati),
            quantity=int(lot),
            capital_at_entry=float(sermaye),
            stop_loss=_opsiyonel_fiyat(float(stop)),
            target_price=_opsiyonel_fiyat(float(hedef)),
            fees=float(masraf),
            signal_class=sinyal.strip(),
            late_entry=bool(gec_giris),
            averaging_down=bool(kaybedene_ekleme),
            overextended_entry=bool(asiri_yukselmis),
            notes=notlar.strip(),
        )
        depo.save(kayit)
        st.session_state["islem_gunlugu_bildirimi"] = (
            f"{kayit.symbol.removesuffix('.IS')} işlemi günlüğe kaydedildi."
        )
        st.rerun()
    except (ValueError, TypeError, TradeJournalError) as hata:
        st.error(str(hata))


def _islem_csv_araclari(
    depo: TradeJournalStore,
    kayitlar: tuple[TradeRecord, ...],
) -> None:
    st.subheader("CSV içe ve dışa aktarma")
    st.caption(f"Yerel günlük dosyası: {depo.file_path}")
    sol, sag = st.columns(2)
    with sol:
        st.download_button(
            "CSV şablonunu indir",
            data=csv_template_bytes(),
            file_name="Hisse-Robotu-Islem-Gunlugu-Sablonu.csv",
            mime="text/csv",
            width="stretch",
        )
    with sag:
        st.download_button(
            "Mevcut günlüğü CSV olarak indir",
            data=records_to_csv_bytes(kayitlar),
            file_name="Hisse-Robotu-Islem-Gunlugu.csv",
            mime="text/csv",
            width="stretch",
        )

    yuklenen = st.file_uploader(
        "İşlem günlüğü CSV dosyası",
        type=("csv",),
        help="Şablondaki sütun adlarını koruyun. Ondalık ayırıcı nokta veya virgül olabilir.",
    )
    if yuklenen is not None and st.button(
        "CSV kayıtlarını günlüğe ekle", type="primary", width="stretch"
    ):
        try:
            yeni_kayitlar = records_from_csv_bytes(yuklenen.getvalue())
            eklenen = depo.save_many(yeni_kayitlar)
            st.session_state["islem_gunlugu_bildirimi"] = (
                f"CSV dosyasından {eklenen} işlem kaydı eklendi."
            )
            st.rerun()
        except (ValueError, TypeError, TradeJournalError) as hata:
            st.error(str(hata))


def _guvenlik_karari_goster(karar: SafetyDecision) -> None:
    if karar.allowed:
        st.success(
            "İşlem güvenlik kurallarını geçiyor. Bu sonuç kazanç garantisi veya "
            "alım önerisi değildir; yalnızca tanımlı risk sınırlarının aşılmadığını gösterir."
        )
    else:
        st.error("Yeni işlem güvenlik kilidi tarafından engellendi.")

    metrik_izgarasi_goster(
        (
            ("Güvenlik durumu", karar.status),
            ("Pozisyon tutarı", para_yaz(karar.position_amount)),
            ("Pozisyon / sermaye", yuzde_yaz(karar.position_pct)),
            (
                "Planlanan risk",
                "—" if karar.risk_amount is None else para_yaz(karar.risk_amount),
            ),
            (
                "Risk / sermaye",
                "—" if karar.risk_pct is None else yuzde_yaz(karar.risk_pct),
            ),
            (
                "Risk/Getiri",
                "—" if karar.reward_risk is None else f"1:{karar.reward_risk:.2f}",
            ),
            ("Günlük zarar oranı", yuzde_yaz(karar.daily_loss_pct)),
            ("Haftalık zarar oranı", yuzde_yaz(karar.weekly_loss_pct)),
        )
    )
    aciklama_listesi_goster(
        "İşlemi engelleyen nedenler",
        karar.blocking_reasons,
        "Engelleyen kural yok.",
    )
    aciklama_listesi_goster(
        "Uyarılar",
        karar.warnings,
        "Ek uyarı yok.",
    )


def _yeni_islem_on_kontrolu(
    sonuc: LossAnalysisResult,
    politika: SafetyPolicy,
) -> None:
    st.subheader("Yeni işlem ön kontrolü")
    st.warning(
        "Bu ekran emir göndermez. Yalnızca stop, hedef, pozisyon büyüklüğü ve "
        "işlem günlüğündeki günlük/haftalık kayıp sınırlarını kontrol eder."
    )
    with st.form("yeni_islem_guvenlik_formu"):
        sol, sag = st.columns(2)
        with sol:
            sembol = st.text_input("Yeni işlem sembolü", value="THYAO")
            sermaye = st.number_input(
                "Güncel sermaye", min_value=1_000.0, value=100_000.0, step=10_000.0
            )
            giris = st.number_input(
                "Planlanan giriş", min_value=0.01, value=100.0, step=0.25
            )
            lot = st.number_input("Planlanan lot", min_value=1, value=100, step=1)
        with sag:
            stop = st.number_input(
                "Stop-loss (0 = yok)", min_value=0.0, value=95.0, step=0.25
            )
            hedef = st.number_input(
                "Hedef fiyat (0 = yok)", min_value=0.0, value=110.0, step=0.25
            )
            kaybedene_ekleme = st.checkbox("Bu işlem kaybeden pozisyona ekleme")
            asiri_yukselmis = st.checkbox("Hisse aşırı yükselmiş bölgede")
        kontrol = st.form_submit_button(
            "Güvenlik kontrolünü çalıştır", type="primary", width="stretch"
        )

    if not kontrol:
        return
    try:
        teklif = TradeProposal(
            symbol=sembol,
            capital=float(sermaye),
            entry_price=float(giris),
            quantity=int(lot),
            stop_loss=_opsiyonel_fiyat(float(stop)),
            target_price=_opsiyonel_fiyat(float(hedef)),
            averaging_down=bool(kaybedene_ekleme),
            overextended_entry=bool(asiri_yukselmis),
        )
        karar = evaluate_trade_safety(
            teklif,
            context=sonuc.safety_context,
            policy=politika,
        )
        _guvenlik_karari_goster(karar)
    except (ValueError, TypeError) as hata:
        st.error(str(hata))


def islem_kayip_analizi_formu() -> None:
    depo = TradeJournalStore()
    with st.sidebar:
        st.header("Kayıp analizi ve güvenlik")
        hesap_filtresi = st.selectbox(
            "Analiz edilecek hesap",
            options=(GERCEK_HESAP, DENEME_HESABI, "Tümü"),
            index=0,
        )
        degerlendirme_tarihi = st.date_input(
            "Güvenlik değerlendirme tarihi",
            value=datetime.now().date(),
            key="kayip_degerlendirme_tarihi",
        )
        st.markdown("**Güvenlik sınırları**")
        azami_risk = st.number_input(
            "İşlem başına azami risk (%)",
            min_value=0.10,
            max_value=10.0,
            value=1.0,
            step=0.10,
            key="kayip_azami_risk",
        )
        minimum_rr = st.number_input(
            "Minimum risk/getiri",
            min_value=0.50,
            max_value=10.0,
            value=2.0,
            step=0.25,
        )
        azami_pozisyon = st.number_input(
            "Azami pozisyon / sermaye (%)",
            min_value=1.0,
            max_value=100.0,
            value=30.0,
            step=1.0,
        )
        gunluk_limit = st.number_input(
            "Günlük zarar kilidi (%)",
            min_value=0.50,
            max_value=20.0,
            value=2.0,
            step=0.50,
        )
        haftalik_limit = st.number_input(
            "Haftalık zarar kilidi (%)",
            min_value=1.0,
            max_value=50.0,
            value=4.0,
            step=0.50,
        )
        azami_seri = st.number_input(
            "Azami ardışık zarar",
            min_value=1,
            max_value=20,
            value=3,
            step=1,
        )

    bildirim = st.session_state.pop("islem_gunlugu_bildirimi", None)
    if bildirim:
        st.success(bildirim)

    try:
        tum_kayitlar = depo.list_records()
    except TradeJournalError as hata:
        st.error(str(hata))
        return

    kayitlar = tuple(
        item
        for item in tum_kayitlar
        if hesap_filtresi == "Tümü" or item.account_type == hesap_filtresi
    )
    try:
        politika = SafetyPolicy(
            max_risk_per_trade_pct=float(azami_risk),
            min_reward_risk=float(minimum_rr),
            max_position_pct=float(azami_pozisyon),
            daily_loss_limit_pct=float(gunluk_limit),
            weekly_loss_limit_pct=float(haftalik_limit),
            max_consecutive_losses=int(azami_seri),
        )
        sonuc = analyze_trade_losses(
            kayitlar,
            policy=politika,
            evaluation_date=degerlendirme_tarihi,
        )
    except (ValueError, TypeError) as hata:
        st.error(str(hata))
        return

    st.header("İşlem Kayıp Analizi ve Güvenlik Kilidi")
    st.info(
        "Analiz yalnızca günlüğe girilen tamamlanmış işlemleri kullanır. Eksik veya "
        "yanlış kayıtlar sonucu değiştirir. Sistem zararları geri kazanmayı veya gelecek "
        "işlemlerde kârı garanti etmez."
    )
    ozet_tab, ekle_tab, csv_tab, kontrol_tab = st.tabs(
        ("Kayıp özeti", "İşlem ekle", "CSV aktarımı", "Yeni işlem ön kontrolü")
    )
    with ozet_tab:
        if not kayitlar:
            st.warning(
                f"{hesap_filtresi} hesabında analiz edilecek tamamlanmış işlem yok. "
                "İşlem ekle veya CSV aktarımı sekmesini kullanın."
            )
        else:
            _kayip_ozeti_goster(sonuc, kayitlar, depo)
    with ekle_tab:
        _islem_kaydi_ekle(depo)
    with csv_tab:
        _islem_csv_araclari(depo, tum_kayitlar)
    with kontrol_tab:
        _yeni_islem_on_kontrolu(sonuc, politika)


def piyasa_rejimi_formu() -> None:
    """XU100, XU030 ve XUTUM için günlük/haftalık piyasa rejimini gösterir."""
    with st.sidebar:
        st.subheader("Piyasa rejimi")
        st.caption(
            "Endeksler için günlük ve haftalık veri zorunludur. "
            "Saatlik veri bulunamazsa analiz durmaz."
        )
        baslat = st.button("Piyasa rejimini analiz et", type="primary")

    st.header("Piyasa Rejimi ve Endeks Analizi")
    st.info(
        "Bu panel kısa vadeli hisse taramasından önce piyasa ortamını "
        "Pozitif, Seçici veya Riskli olarak sınıflandırır. Endeks için "
        "lot, giriş, stop veya hedef üretmez."
    )
    if not baslat:
        st.caption(
            "XU100, XU030 ve XUTUM analizini başlatmak için "
            "sol menüdeki düğmeye basın."
        )
        return

    with st.spinner("Endeks verileri ve piyasa rejimi hesaplanıyor..."):
        try:
            sonuc = MarketRegimeDashboardService().calistir()
        except MarketRegimeDashboardError as hata:
            st.error(str(hata))
            return

    ana = sonuc.ana_rejim
    rejim_baglami = piyasa_rejimi_baglami_olustur(sonuc)
    st.session_state[PIYASA_REJIMI_BAGLAMI_KEY] = (
        rejim_baglami.as_dict()
    )
    if rejim_baglami.gecerli:
        st.session_state["aktif_piyasa_rejimi"] = ana.rejim
    else:
        st.session_state.pop("aktif_piyasa_rejimi", None)
        st.session_state.pop(MOMENTUM_DISCOVERY_RESULT_KEY, None)
        st.session_state.pop(MOMENTUM_DISCOVERY_SIGNATURE_KEY, None)

    if sonuc.eksik_endeksler:
        st.warning(
            "Yardımcı endeks verisi alınamadı: "
            + ", ".join(sonuc.eksik_endeksler)
            + ". BIST 100 ana rejimi kullanılabilir; güven düzeyi "
            "eksik veriyi yansıtır."
        )

    metrik_izgarasi_goster(
        (
            ("BIST 100 rejimi", ana.rejim),
            ("Toplam skor", f"{ana.toplam_skor}/100"),
            ("Güven düzeyi", ana.guven_duzeyi),
            ("Son veri tarihi", tarih_saat_yaz(ana.analiz_tarihi)),
            ("Veri kaynağı", ana.veri_kaynagi),
            ("Kaynak zinciri", " → ".join(ana.kaynak_sirasi)),
            ("Yeniden deneme", str(ana.yeniden_deneme_sayisi)),
            (
                "İndirme süresi",
                f"{ana.toplam_indirme_suresi_saniye:.2f} sn",
            ),
        )
    )

    if rejim_baglami.gecerli:
        st.success(
            "Bu rejim bağlamı Momentum Keşif ekranına güvenli biçimde "
            "aktarılabilir."
        )
    else:
        st.error(
            "Bu rejim Momentum Keşif'e aktarılmadı: "
            + rejim_baglami.gecersizlik_nedeni
        )

    if ana.rejim == REJIM_POZITIF:
        st.success(
            "Kısa vadeli işlem ortamı pozitif; yine de yalnızca detay "
            "teyit alan hisseler değerlendirilmelidir."
        )
    elif ana.rejim == REJIM_SECICI:
        st.warning(
            "Kısa vadeli işlem ortamı seçici; güçlü trend, hacim ve "
            "kırılım teyidi olmayan hisseler elenmelidir."
        )
    else:
        st.error(
            "Kısa vadeli işlem ortamı riskli; yeni pozisyonlar için "
            "korumacı yaklaşım gerekir."
        )

    tablo = [
        {
            "Endeks": f"{item.sembol} · {item.ad}",
            "Kaynak": item.yahoo_sembolu,
            "Veri durumu": (
                "Güncel" if not item.veri_tazeligi.kilitli else "Kilitli"
            ),
            "Skor": item.toplam_skor,
            "Rejim": item.rejim,
            "Güven": item.guven_duzeyi,
            "Günlük": item.gunluk_yon,
            "Haftalık": item.haftalik_yon,
            "Saatlik": (
                item.saatlik_yon
                if item.saatlik_kullanilabilir
                else "Veri yok — analiz sürdü"
            ),
            "Veri tarihi": tarih_saat_yaz(item.analiz_tarihi),
        }
        for item in sonuc.sonuclar
    ]
    st.dataframe(pd.DataFrame(tablo), width="stretch", hide_index=True)

    secili = st.selectbox(
        "Endeks ayrıntısı",
        options=[item.sembol for item in sonuc.sonuclar],
        format_func=lambda kod: next(
            f"{x.sembol} · {x.ad}"
            for x in sonuc.sonuclar
            if x.sembol == kod
        ),
    )
    item = next(x for x in sonuc.sonuclar if x.sembol == secili)

    bilesenler = (
        item.trend,
        item.momentum,
        item.hacim,
        item.kirilim,
        item.genislik,
    )
    for baslangic in range(0, len(bilesenler), 2):
        sutunlar = st.columns(2)
        for sutun, bilesen in zip(
            sutunlar,
            bilesenler[baslangic : baslangic + 2],
        ):
            sutun.metric(
                bilesen.ad,
                f"{bilesen.skor}/{bilesen.maksimum_skor}",
                bilesen.durum,
            )

    veri_durumu = (
        "Güncel" if not item.veri_tazeligi.kilitli else "Kilitli"
    )
    st.markdown("### Veri güvenliği")
    st.caption(
        f"Kaynak: {item.yahoo_sembolu} · "
        f"Son veri: {tarih_saat_yaz(item.analiz_tarihi)} · "
        f"Durum: {veri_durumu} · "
        f"Güven: {item.guven_duzeyi}"
    )
    if item.veri_tazeligi.kilitli:
        st.error(item.veri_tazeligi.aciklama)
    else:
        st.success(item.veri_tazeligi.aciklama)

    with st.expander("Olumlu gerekçeler", expanded=True):
        if item.pozitif_nedenler:
            for metin in item.pozitif_nedenler:
                st.markdown(f"- {metin}")
        else:
            st.write("Belirgin olumlu gerekçe yok.")

    with st.expander("Riskler ve eksik teyitler", expanded=True):
        if item.riskler:
            for metin in item.riskler:
                st.markdown(f"- {metin}")
        else:
            st.write("Belirgin risk kaydı yok.")


def _temel_deger_yaz(deger: object) -> str:
    if deger is None:
        return "Hesaplanamadı"
    try:
        return f"{float(deger):,.2f}"
    except (TypeError, ValueError):
        return str(deger)


def _temel_yuzde_yaz(deger: object) -> str:
    if deger is None:
        return "Hesaplanamadı"
    return f"%{float(deger):,.2f}"


def _buyume_tablosu(snapshot) -> pd.DataFrame:
    satirlar: list[dict[str, object]] = []

    for baslik, buyume in (
        ("Önceki çeyrek", snapshot.quarter_growth),
        ("Geçen yıl aynı dönem", snapshot.annual_growth),
    ):
        if buyume is None:
            continue
        satirlar.extend(
            (
                {
                    "Karşılaştırma": baslik,
                    "Gösterge": "Hasılat",
                    "Değişim (%)": buyume.revenue_growth,
                },
                {
                    "Karşılaştırma": baslik,
                    "Gösterge": "FAVÖK",
                    "Değişim (%)": buyume.ebitda_growth,
                },
                {
                    "Karşılaştırma": baslik,
                    "Gösterge": "Net kâr",
                    "Değişim (%)": buyume.net_income_growth,
                },
                {
                    "Karşılaştırma": baslik,
                    "Gösterge": "Özsermaye",
                    "Değişim (%)": buyume.equity_growth,
                },
                {
                    "Karşılaştırma": baslik,
                    "Gösterge": "Faaliyet nakit akışı",
                    "Değişim (%)": (
                        buyume.operating_cash_flow_growth
                    ),
                },
            )
        )

    return pd.DataFrame(satirlar)


def _donem_grafigi(periods) -> pd.DataFrame:
    satirlar = []
    for item in sorted(periods, key=lambda value: value.period_end):
        satirlar.append(
            {
                "Dönem": item.period_key,
                "Hasılat": float(item.revenue),
                "FAVÖK": float(item.ebitda),
                "Net kâr": float(item.net_income),
                "Özsermaye": float(item.total_equity),
            }
        )

    if not satirlar:
        return pd.DataFrame()

    return pd.DataFrame(satirlar).set_index("Dönem")


def temel_analiz_formu() -> None:
    st.header("Temel Analiz ve Bilanço")
    st.caption(
        "Şirket finansallarını dönemsel olarak karşılaştırır. "
        "Bu ekran teknik taramaya zorunlu filtre uygulamaz."
    )

    kap_api_durumu = validate_kap_api_configuration(
        load_kap_api_configuration()
    )

    st.subheader("KAP API erişim durumu")
    metrik_izgarasi_goster(
        (
            (
                "Erişim modu",
                kap_api_durumu.configuration.mode.value,
            ),
            (
                "API adresi",
                (
                    kap_api_durumu.configuration.base_url
                    or "Tanımlı değil"
                ),
            ),
            (
                "İstemci",
                kap_api_durumu.configuration.masked_client_id,
            ),
            (
                "Canlı güncelleme",
                (
                    "Hazır"
                    if not kap_api_durumu.locked
                    else "Kilitli"
                ),
            ),
        )
    )

    if kap_api_durumu.locked:
        st.warning(kap_api_durumu.explanation)
        if kap_api_durumu.missing_fields:
            st.caption(
                "Eksik yapılandırma: "
                + ", ".join(kap_api_durumu.missing_fields)
            )
    else:
        st.success(kap_api_durumu.explanation)

    st.caption(
        "API anahtarı ve istemci bilgileri ekranda gösterilmez "
        "ve proje dosyalarına kaydedilmez."
    )
    st.info(
        "Canlı KAP veri çekme bu aşamada devre dışıdır. "
        "Manuel CSV/JSON bilanço yükleme yolu aktiftir."
    )

    yuklenen = st.file_uploader(
        "Bilanço dosyası",
        type=("csv", "json"),
        accept_multiple_files=False,
        key="temel_analiz_dosyasi",
        help=(
            "Sprint-54 bilanço şemasına uygun CSV veya JSON "
            "dosyası yükleyin."
        ),
    )

    if yuklenen is None:
        st.info(
            "Analiz için CSV veya JSON bilanço dosyası yükleyin. "
            "Örnek dosya: backend/data/fundamental_sample.csv"
        )
        return

    try:
        uzanti = Path(yuklenen.name).suffix.lower()
        icerik = yuklenen.getvalue()

        if uzanti == ".csv":
            donemler = periods_from_csv_bytes(icerik)
        elif uzanti == ".json":
            donemler = periods_from_json_bytes(icerik)
        else:
            raise FundamentalDataError(
                "Bilanço dosyası CSV veya JSON olmalıdır."
            )
    except (
        FundamentalDataError,
        ValueError,
        TypeError,
        UnicodeError,
    ) as hata:
        st.error(f"Bilanço dosyası doğrulanamadı: {hata}")
        return

    semboller = sorted({item.symbol for item in donemler})
    sembol = st.selectbox(
        "Şirket",
        options=semboller,
        key="temel_analiz_sembol",
    )
    sirket_donemleri = [
        item for item in donemler if item.symbol == sembol
    ]

    tazelik = evaluate_fundamental_freshness(sirket_donemleri)
    if tazelik.locked:
        st.error(tazelik.explanation)
    else:
        st.success(tazelik.explanation)

    metrik_izgarasi_goster(
        (
            ("Finansal dönem", str(len(sirket_donemleri))),
            (
                "Son dönem",
                (
                    tarih_saat_yaz(tazelik.latest_period_end)
                    if tazelik.latest_period_end is not None
                    else "Yok"
                ),
            ),
            ("Tazelik durumu", tazelik.status),
            (
                "Veri yaşı",
                (
                    f"{tazelik.age_days} gün"
                    if tazelik.age_days is not None
                    else "Bilinmiyor"
                ),
            ),
        )
    )

    if tazelik.locked:
        st.warning(
            "Tazelik kilidi nedeniyle temel oranlar ve büyüme "
            "değerlendirmesi üretilmedi."
        )
        return

    try:
        snapshot = build_fundamental_snapshot(
            sirket_donemleri,
            source_metadata={
                "filename": yuklenen.name,
                "record_count": str(len(sirket_donemleri)),
            },
        )
    except (ValueError, TypeError) as hata:
        st.error(f"Temel analiz özeti üretilemedi: {hata}")
        return

    latest = snapshot.latest
    ratios = snapshot.ratios
    kalite = calculate_fundamental_quality(snapshot, tazelik)

    st.subheader("Temel kalite skoru")
    if kalite.locked or kalite.total_score is None:
        st.warning(kalite.explanation)
    else:
        try:
            skor_kayit_sonucu = temel_skor_deposu().save(
                periods=sirket_donemleri,
                score=kalite,
            )
            st.caption(
                "Temel skor yerel depoya kaydedildi · "
                f"eklenen {skor_kayit_sonucu.inserted} · "
                f"güncellenen {skor_kayit_sonucu.updated} · "
                f"değişmeyen {skor_kayit_sonucu.unchanged}."
            )
        except (
            FundamentalScoreStoreError,
            ValueError,
        ) as hata:
            st.warning(f"Temel skor kaydedilemedi: {hata}")

        metrik_izgarasi_goster(
            (
                ("Toplam kalite skoru", f"{kalite.total_score}/100"),
                ("Kalite sınıfı", kalite.grade),
                (
                    "Kârlılık",
                    f"{kalite.profitability.score}/"
                    f"{kalite.profitability.maximum_score}",
                ),
                (
                    "Büyüme",
                    f"{kalite.growth.score}/"
                    f"{kalite.growth.maximum_score}",
                ),
                (
                    "Borçluluk",
                    f"{kalite.leverage.score}/"
                    f"{kalite.leverage.maximum_score}",
                ),
                (
                    "Likidite",
                    f"{kalite.liquidity.score}/"
                    f"{kalite.liquidity.maximum_score}",
                ),
                (
                    "Nakit akışı",
                    f"{kalite.cash_flow.score}/"
                    f"{kalite.cash_flow.maximum_score}",
                ),
            )
        )
        st.caption(kalite.explanation)

    st.subheader("Temel skor geçmişi")
    try:
        skor_gecmisi = temel_skor_deposu().load_history(
            latest.symbol
        )
    except FundamentalScoreStoreError as hata:
        st.warning(f"Temel skor geçmişi okunamadı: {hata}")
        skor_gecmisi = ()

    if not skor_gecmisi:
        st.info(
            "Bu şirket için kayıtlı temel skor geçmişi bulunmuyor."
        )
    else:
        gecmis_tablosu = pd.DataFrame(
            history_rows(skor_gecmisi)
        )
        st.dataframe(
            gecmis_tablosu,
            width="stretch",
            hide_index=True,
        )

        skor_grafigi = gecmis_tablosu.set_index("Dönem")[
            [
                "Toplam skor",
                "Kârlılık",
                "Büyüme",
                "Borçluluk",
                "Likidite",
                "Nakit akışı",
            ]
        ]
        st.line_chart(
            skor_grafigi,
            width="stretch",
        )

        son_degisiklik = latest_score_change(skor_gecmisi)
        if son_degisiklik is None:
            st.caption(
                "Skor değişimi için en az iki kayıtlı dönem gerekir."
            )
        else:
            degisim_yonu = (
                "arttı"
                if son_degisiklik.total_change > 0
                else "azaldı"
                if son_degisiklik.total_change < 0
                else "değişmedi"
            )
            st.info(
                f"Toplam temel skor "
                f"{son_degisiklik.previous_period} → "
                f"{son_degisiklik.current_period} döneminde "
                f"{abs(son_degisiklik.total_change)} puan "
                f"{degisim_yonu}."
            )
            if son_degisiklik.improving_components:
                st.caption(
                    "Güçlenen bileşenler: "
                    + ", ".join(
                        son_degisiklik.improving_components
                    )
                )
            if son_degisiklik.weakening_components:
                st.caption(
                    "Zayıflayan bileşenler: "
                    + ", ".join(
                        son_degisiklik.weakening_components
                    )
                )

    st.subheader("Şirket bazlı temel skor karşılaştırması")
    try:
        karsilastirilabilir_skorlar = (
            temel_skor_deposu().load_comparable_latest()
        )
    except FundamentalScoreStoreError as hata:
        st.warning(
            f"Şirket karşılaştırması okunamadı: {hata}"
        )
        karsilastirilabilir_skorlar = ()

    if len(karsilastirilabilir_skorlar) < 2:
        st.info(
            "Aynı güncel döneme ait en az iki şirket skoru "
            "bulunduğunda karşılaştırma tablosu gösterilir."
        )
    else:
        st.dataframe(
            pd.DataFrame(
                comparison_rows(karsilastirilabilir_skorlar)
            ),
            width="stretch",
            hide_index=True,
        )
        st.caption(
            "Şirket karşılaştırması yalnızca aynı güncel bilanço "
            "dönemindeki kayıtları kullanır ve alım/satım sinyali "
            "üretmez."
        )

    st.subheader("Finansal oran ve sektör referansı")
    st.caption(
        "Sektör karşılaştırması yalnızca yüklenen bilanço "
        "verileri ile kullanıcı tarafından sağlanan sektör "
        "referansını kullanır."
    )

    sektor_dosyasi = st.file_uploader(
        "Sektör referans dosyası",
        type=("csv",),
        accept_multiple_files=False,
        key="temel_analiz_sektor_referansi",
        help=(
            "Zorunlu sütunlar: symbol, sector. "
            "F/K ve PD/DD için isteğe bağlı market_cap "
            "sütunu kullanılabilir."
        ),
    )

    if sektor_dosyasi is None:
        st.info(
            "Sektör medyanı karşılaştırması için CSV referans "
            "dosyası yükleyin. Sektör veya piyasa değeri "
            "tahmin edilmez."
        )
    else:
        try:
            sektor_referanslari = references_from_csv_bytes(
                sektor_dosyasi.getvalue()
            )
            oran_referanslari = (
                build_company_ratio_references(
                    donemler,
                    sektor_referanslari,
                )
            )
            sektor_karsilastirmasi = (
                compare_company_to_sector(
                    oran_referanslari,
                    latest.symbol,
                )
            )
        except (
            SectorReferenceError,
            ValueError,
            TypeError,
            UnicodeError,
        ) as hata:
            st.warning(
                f"Sektör karşılaştırması üretilemedi: {hata}"
            )
        else:
            metrik_izgarasi_goster(
                (
                    (
                        "Şirket",
                        sektor_karsilastirmasi.symbol,
                    ),
                    (
                        "Sektör",
                        sektor_karsilastirmasi.sector,
                    ),
                    (
                        "Karşılaştırma dönemi",
                        sektor_karsilastirmasi.period_key,
                    ),
                    (
                        "Aynı dönem şirket sayısı",
                        str(sektor_karsilastirmasi.peer_count),
                    ),
                )
            )
            st.dataframe(
                pd.DataFrame(
                    sector_comparison_rows(
                        sektor_karsilastirmasi
                    )
                ),
                width="stretch",
                hide_index=True,
                column_config={
                    "Şirket": st.column_config.NumberColumn(
                        "Şirket",
                        format="%.2f",
                    ),
                    "Sektör medyanı": (
                        st.column_config.NumberColumn(
                            "Sektör medyanı",
                            format="%.2f",
                        )
                    ),
                },
            )
            st.caption(
                "F/K ve PD/DD yalnızca market_cap sağlandığında "
                "hesaplanır. Oran konumu tek başına olumlu veya "
                "olumsuz kabul edilmez ve alım/satım sinyali "
                "üretmez."
            )

            st.subheader(
                "Sektör bazlı temel skor sıralaması"
            )
            st.caption(
                "Sıralama yalnızca aynı güncel bilanço "
                "dönemindeki kayıtlı ve kilitsiz temel skorları "
                "kullanır."
            )

            siralama_sektoru = st.selectbox(
                "Sıralanacak sektör",
                options=sorted(
                    {
                        reference.sector
                        for reference in (
                            sektor_referanslari.values()
                        )
                    }
                ),
                index=(
                    sorted(
                        {
                            reference.sector
                            for reference in (
                                sektor_referanslari.values()
                            )
                        }
                    ).index(
                        sektor_karsilastirmasi.sector
                    )
                    if sektor_karsilastirmasi.sector
                    in {
                        reference.sector
                        for reference in (
                            sektor_referanslari.values()
                        )
                    }
                    else 0
                ),
                key="temel_skor_sektor_siralamasi",
            )

            try:
                sektor_skor_siralamasi = (
                    build_sector_score_ranking(
                        karsilastirilabilir_skorlar,
                        sektor_referanslari,
                        siralama_sektoru,
                        minimum_peer_count=3,
                    )
                )
            except SectorScoreRankingError as hata:
                st.info(
                    f"Sektör temel skor sıralaması "
                    f"oluşturulamadı: {hata}"
                )
            else:
                metrik_izgarasi_goster(
                    (
                        (
                            "Sektör",
                            sektor_skor_siralamasi.sector,
                        ),
                        (
                            "Dönem",
                            sektor_skor_siralamasi.period_key,
                        ),
                        (
                            "Şirket sayısı",
                            str(
                                sektor_skor_siralamasi.peer_count
                            ),
                        ),
                        (
                            "Sektör medyanı",
                            f"{sektor_skor_siralamasi.sector_median:.1f}",
                        ),
                    )
                )
                st.dataframe(
                    pd.DataFrame(
                        sector_score_ranking_rows(
                            sektor_skor_siralamasi
                        )
                    ),
                    width="stretch",
                    hide_index=True,
                )
                st.caption(
                    "Güçlü, Dengeli, İzlenmeli ve Zayıf "
                    "sınıfları temel kalite skorunu özetler. "
                    "Bu sıralama tek başına alım/satım sinyali "
                    "üretmez."
                )

    st.subheader(f"{latest.symbol} · {latest.period_key}")
    st.caption(
        f"Dönem sonu: {tarih_saat_yaz(latest.period_end)} · "
        f"Para birimi: {latest.currency} · "
        f"Kaynak: {latest.source}"
    )

    metrik_izgarasi_goster(
        (
            ("Hasılat", _temel_deger_yaz(latest.revenue)),
            ("FAVÖK", _temel_deger_yaz(latest.ebitda)),
            ("Net kâr", _temel_deger_yaz(latest.net_income)),
            ("Özsermaye", _temel_deger_yaz(latest.total_equity)),
        )
    )

    st.subheader("Kârlılık ve finansal yapı")
    oran_tablosu = pd.DataFrame(
        (
            {
                "Gösterge": "Brüt kâr marjı",
                "Değer": _temel_yuzde_yaz(ratios.gross_margin),
            },
            {
                "Gösterge": "Faaliyet kâr marjı",
                "Değer": _temel_yuzde_yaz(
                    ratios.operating_margin
                ),
            },
            {
                "Gösterge": "FAVÖK marjı",
                "Değer": _temel_yuzde_yaz(ratios.ebitda_margin),
            },
            {
                "Gösterge": "Net kâr marjı",
                "Değer": _temel_yuzde_yaz(ratios.net_margin),
            },
            {
                "Gösterge": "ROE",
                "Değer": _temel_yuzde_yaz(ratios.roe),
            },
            {
                "Gösterge": "ROA",
                "Değer": _temel_yuzde_yaz(ratios.roa),
            },
            {
                "Gösterge": "Cari oran",
                "Değer": _temel_deger_yaz(ratios.current_ratio),
            },
            {
                "Gösterge": "Borç / özsermaye",
                "Değer": _temel_deger_yaz(
                    ratios.debt_to_equity
                ),
            },
            {
                "Gösterge": "Net borç",
                "Değer": _temel_deger_yaz(ratios.net_debt),
            },
            {
                "Gösterge": "Net borç / FAVÖK",
                "Değer": _temel_deger_yaz(
                    ratios.net_debt_to_ebitda
                ),
            },
            {
                "Gösterge": "Serbest nakit akışı",
                "Değer": _temel_deger_yaz(
                    ratios.free_cash_flow
                ),
            },
            {
                "Gösterge": "Serbest nakit akışı marjı",
                "Değer": _temel_yuzde_yaz(
                    ratios.free_cash_flow_margin
                ),
            },
        )
    )
    st.dataframe(
        oran_tablosu,
        width="stretch",
        hide_index=True,
    )

    grafik = _donem_grafigi(sirket_donemleri)
    if not grafik.empty:
        st.subheader("Dönemsel gelişim")
        st.line_chart(grafik, width="stretch")

    buyume = _buyume_tablosu(snapshot)
    st.subheader("Dönem karşılaştırmaları")
    if buyume.empty:
        st.info(
            "Önceki çeyrek veya geçen yıl aynı dönem verisi "
            "bulunmadığı için büyüme karşılaştırması üretilemedi."
        )
    else:
        st.dataframe(
            buyume,
            width="stretch",
            hide_index=True,
            column_config={
                "Değişim (%)": st.column_config.NumberColumn(
                    "Değişim (%)",
                    format="%.2f",
                )
            },
        )

    st.subheader("Finansal kalite uyarıları")
    if snapshot.quality_flags:
        for uyari in snapshot.quality_flags:
            st.warning(uyari)
    else:
        st.success(
            "Tanımlı temel analiz kurallarına göre belirgin "
            "finansal kalite uyarısı bulunmadı."
        )


def main() -> None:
    st.set_page_config(
        page_title="Hisse Robotu",
        page_icon="📈",
        layout="wide",
    )

    arayuz_stili_uygula()

    st.title("Hisse Robotu")
    st.caption(
        "Gerçek veri backtest paneli · "
        "Kişisel analiz amaçlıdır, yatırım tavsiyesi değildir."
    )

    with st.sidebar:
        analiz_modu = st.radio(
            "Analiz modu",
            options=ANALIZ_MODLARI,
            index=0,
        )

    if analiz_modu == "Tek Hisse":
        tek_hisse_formu()
    elif analiz_modu == "Güncel Teknik Analiz":
        guncel_teknik_analiz_formu()
    elif analiz_modu == "Temel Analiz":
        temel_analiz_formu()
    elif analiz_modu == "Piyasa Rejimi":
        piyasa_rejimi_formu()
    elif analiz_modu == "Momentum Keşif":
        momentum_kesif_formu()
    elif analiz_modu == "BIST Toplu Tarama":
        bist_toplu_tarama_formu()
    elif analiz_modu == "Açık Pozisyon İzleme":
        acik_pozisyon_izleme_formu()
    elif analiz_modu == "İşlem Kayıp Analizi":
        islem_kayip_analizi_formu()
    elif analiz_modu == "Aynı Veri Karşılaştırması":
        ayni_veri_karsilastirma_formu()
    elif analiz_modu == "Çoklu Hisse Portföyü":
        portfoy_formu()
    else:
        analiz_gecmisi_goster()


if __name__ == "__main__":
    main()
