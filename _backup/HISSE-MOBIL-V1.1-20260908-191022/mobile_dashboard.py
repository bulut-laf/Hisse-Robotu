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
        button[kind="secondary"], button[kind="primary"] { min-height: 2.7rem; }
        @media (max-width: 600px) {
            .block-container { padding-left: 0.55rem; padding-right: 0.55rem; }
            h1 { font-size: 1.7rem !important; }
            h2 { font-size: 1.4rem !important; }
            h3 { font-size: 1.2rem !important; }
            [data-testid="column"] { min-width: 0 !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_fund_center() -> None:
    from backend.app.funds.portfolio_tracking import fund_portfolio_snapshot_store
    from backend.app.funds.ui_live_refresh import refresh_fund_analysis_if_requested
    from backend.app.funds.canonical_result_store import (
        FundCanonicalResultStoreError,
        load_last_good_fund_analysis_results,
        save_last_good_fund_analysis_results,
    )
    from backend.app.funds.tefas_universe_nonblocking_refresh import (
        queue_tefas_universe_refresh,
    )
    from backend.app.funds.live_pipeline import get_last_live_fund_metadata
    from backend.app.ui.fund_analysis_center import render_fund_analysis_center

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

    st.caption(
        "TEFAS/fon araştırma ekranı. Son iyi veri korunur; otomatik AL/SAT yetkisi yoktur."
    )
    refresh_requested = st.button(
        "TEFAS verisini şimdi güncelle",
        key="mobile_fund_refresh",
        width="stretch",
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
    elif current_live_results:
        auto_due = True

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
        elif refresh_state.status in ("FAILED", "TIMEOUT"):
            st.caption("Otomatik TEFAS yenilemesi izole edildi; son iyi veri korunuyor.")

    if refresh_requested:
        st.session_state["fund_analysis_auto_refresh_attempt_at"] = now_utc
        with st.spinner("TEFAS canlı fon verisi güncelleniyor..."):
            refresh_outcome = refresh_fund_analysis_if_requested(
                requested=True,
                current_results=current_live_results,
            )
        if refresh_outcome.error_message:
            st.error(
                "TEFAS canlı fon verisi güncellenemedi; mevcut ekran korunuyor. "
                + refresh_outcome.error_message
            )
        elif refresh_outcome.refreshed:
            save_last_good_fund_analysis_results(refresh_outcome.results)
            st.session_state[live_results_key] = refresh_outcome.results
            current_live_results = refresh_outcome.results
            st.success(f"TEFAS canlı fon analizi güncellendi: {len(refresh_outcome.results)} fon.")

    render_fund_analysis_center(
        st,
        current_live_results,
        portfolio_store=fund_portfolio_snapshot_store(),
        fund_metadata=get_last_live_fund_metadata(),
    )


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

    st.title("Hisse Robotu Mobil")
    st.caption("Kişisel kullanım · masaüstündeki ana Hisse Robotu motorunu kullanır.")

    selected = st.selectbox(
        "Bölüm",
        MOBILE_MODULES,
        index=0,
        key="mobile_section",
    )
    st.divider()

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
