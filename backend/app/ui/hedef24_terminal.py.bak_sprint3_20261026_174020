from __future__ import annotations

from datetime import date
from pathlib import Path
import pandas as pd
import streamlit as st

from backend.app.funds.hedef24_store import Hedef24Store, PortfolioValidationError
from backend.app.funds.hedef24_analysis import technical_signal

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PORTFOLIO_PATH = PROJECT_ROOT / "_discovery" / "erste_hungary" / "hedef24_portfolio.json"
SEED_PATH = PROJECT_ROOT / "_discovery" / "erste_hungary" / "hedef24_portfolio_seed.json"


def _fmt(value, digits=4):
    if value in (None, ""):
        return "—"
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def render_hedef24_terminal() -> None:
    st.header("🎯 Hedef 24 — Portföy, Teknik Analiz ve AL/SAT Karar Desteği")
    store = Hedef24Store(PORTFOLIO_PATH)
    try:
        records = store.list_records()
        if not records and SEED_PATH.exists():
            if st.button("24 fonluk başlangıç listesini içe aktar", key="h24_import_seed"):
                count = store.import_seed(SEED_PATH)
                st.success(f"{count} fon içe aktarıldı.")
                st.rerun()
    except PortfolioValidationError as exc:
        st.error(str(exc))
        return

    data = store.load()
    records = store.list_records()
    history = data.get("nav_history", [])
    st.caption(f"Kayıt: {len(records)}/24 · NAV gözlemi: {len(history)} · Emir gönderimi: KAPALI (NONE)")
    if records:
        rows = []
        for r in records:
            perf = store.performance(r["slot"])
            rows.append({
                "Slot": r.get("slot"), "Fon": r.get("fund_name") or "Fon adı eksik",
                "ISIN": r.get("isin") or "EKSİK", "Döviz": r.get("currency") or "—",
                "Alış tarihi": r.get("purchase_date") or "—",
                "Alış NAV": r.get("purchase_nav") or "—", "Adet": r.get("units") or "—",
                "Son NAV": r.get("latest_nav") or "—",
                "NAV tarihi": r.get("latest_nav_date") or "—",
                "K/Z %": perf.get("pnl_percent", "—") if perf.get("available") else "—",
                "Veri durumu": r.get("data_status", "UNKNOWN"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Fon bilgileri ve maliyet")
    if records:
        slots = [int(r["slot"]) for r in records]
        slot = st.selectbox("Düzenlenecek fon — slot", slots, format_func=lambda x: f'{x}: {next((r.get("fund_name") or "Fon adı eksik" for r in records if r["slot"] == x), "")}', key="h24_edit_slot")
        rec = next(r for r in records if int(r["slot"]) == slot)
        with st.form("h24_edit_form"):
            name = st.text_input("Fon adı", value=rec.get("fund_name") or "")
            isin = st.text_input("ISIN (12 karakter; doğrulama ayrı yapılır)", value=rec.get("isin") or "")
            currency = st.text_input("Döviz", value=rec.get("currency") or "")
            purchase_date = st.text_input("Alış tarihi (YYYY-MM-DD)", value=rec.get("purchase_date") or "")
            purchase_nav = st.text_input("Alış NAV", value=rec.get("purchase_nav") or "")
            units = st.text_input("Adet", value=rec.get("units") or "")
            notes = st.text_area("Not", value=rec.get("notes") or "")
            saved = st.form_submit_button("Fon bilgilerini kaydet")
        if saved:
            try:
                store.update_fund(slot, fund_name=name, isin=isin or None, currency=currency or None,
                                  purchase_date=purchase_date or None, purchase_nav=purchase_nav or None,
                                  units=units or None, notes=notes)
                st.success("Fon bilgileri kaydedildi.")
                st.rerun()
            except PortfolioValidationError as exc:
                st.error(str(exc))

    with st.expander("Fon ekle / portföyden çıkar"):
        c1, c2 = st.columns(2)
        with c1:
            with st.form("h24_add_form"):
                add_name = st.text_input("Yeni fon adı")
                add_isin = st.text_input("ISIN (opsiyonel)")
                add_currency = st.text_input("Döviz (opsiyonel)")
                add_ok = st.form_submit_button("Fonu ekle")
            if add_ok:
                try:
                    store.add_fund(add_name, add_isin or None, currency=add_currency or None)
                    st.success("Fon eklendi.")
                    st.rerun()
                except PortfolioValidationError as exc:
                    st.error(str(exc))
        with c2:
            if records:
                remove_slot = st.selectbox("Çıkarılacak slot", [int(r["slot"]) for r in records], key="h24_remove_slot")
                confirm_remove = st.checkbox("Bu fon kaydını kaldırmayı onaylıyorum", key="h24_confirm_remove")
                if st.button("Fon kaydını kaldır", key="h24_remove_btn"):
                    if not confirm_remove:
                        st.warning("Önce açık onay kutusunu işaretleyin.")
                    else:
                        try:
                            store.remove_fund(remove_slot, confirm=True)
                            st.success("Fon kaydı kaldırıldı.")
                            st.rerun()
                        except PortfolioValidationError as exc:
                            st.error(str(exc))

    st.subheader("Günlük NAV kaydı")
    if records:
        with st.form("h24_nav_form"):
            nav_slot = st.selectbox("NAV girilecek fon", [int(r["slot"]) for r in records], key="h24_nav_slot")
            nav_date = st.date_input("NAV tarihi", value=date.today(), key="h24_nav_date")
            nav = st.number_input("NAV", min_value=0.000001, value=1.0, format="%.6f", key="h24_nav_value")
            nav_currency = st.text_input("NAV dövizi (opsiyonel)", key="h24_nav_currency")
            nav_source = st.text_input("Kaynak / URL / belge adı (zorunlu değil)", key="h24_nav_source")
            nav_ok = st.form_submit_button("NAV kaydet")
        if nav_ok:
            try:
                store.record_nav(nav_slot, nav_date.isoformat(), nav, currency=nav_currency or None, source=nav_source)
                st.success("NAV kaydedildi. Kaynak belirtilmediyse kayıt doğrulanmış sayılmaz.")
                st.rerun()
            except PortfolioValidationError as exc:
                st.error(str(exc))

    st.subheader("Teknik analiz ve AL/SAT karar desteği")
    st.caption("Sinyal yalnızca kaydedilmiş NAV geçmişinden hesaplanır. En az 21 geçerli gözlem gerekir; otomatik emir yoktur.")
    if records:
        choices = [int(r["slot"]) for r in records]
        selected = st.selectbox("Analiz edilecek fon", choices, format_func=lambda x: f'{x}: {next((r.get("fund_name") or "Fon adı eksik" for r in records if r["slot"] == x), "")}', key="h24_analysis_slot")
        fund_hist = sorted([x for x in history if int(x.get("slot", 0)) == selected], key=lambda x: x.get("date", ""))
        result = technical_signal(x.get("nav") for x in fund_hist)
        a, b, c, d = st.columns(4)
        a.metric("Sinyal", result["signal"])
        b.metric("Momentum 20", "—" if result["momentum_20_pct"] is None else f'{result["momentum_20_pct"]:.2f}%')
        c.metric("RSI 14", "—" if result["rsi_14"] is None else f'{result["rsi_14"]:.2f}')
        d.metric("NAV gözlemi", result["observations"])
        st.write(result["reason"])
        if fund_hist:
            st.line_chart(pd.DataFrame([{"Tarih": x["date"], "NAV": float(x["nav"])} for x in fund_hist]).set_index("Tarih"))
        st.info("Bu sinyal yatırım tavsiyesi veya emir değildir. Fon NAV'ı genellikle gecikmeli yayımlanır; veri kaynağı ve tarihi kontrol edilmelidir.")
