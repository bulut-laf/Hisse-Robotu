from __future__ import annotations

import pandas as pd
import streamlit as st

from backend.app.analysis.bist_daily_market import (
    BistDailyMarketResult,
    bist_gunluk_piyasa_olustur,
    bist_ozel_liste_olustur,
    bist_tum_sembollerini_yukle,
    ozel_liste_girdilerini_ayir,
    sembol_eslesmeleri,
    bist_tum_sirket_adlarini_yukle,
)


def _format_price(value: float) -> str:
    return f"{value:,.2f} TL"


def _single_stock_card(row: pd.Series) -> None:
    st.subheader(f"{row['Hisse']} · Günlük Özet")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Son fiyat",
        _format_price(float(row["Son Fiyat"])),
        f"{float(row['Günlük Değişim %']):+.2f}%",
    )
    c2.metric("Açılış", _format_price(float(row["Açılış"])))
    c3.metric("En düşük", _format_price(float(row["En Düşük"])))
    c4.metric("En yüksek", _format_price(float(row["En Yüksek"])))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Önceki kapanış", _format_price(float(row["Önceki Kapanış"])))
    c6.metric("Değişim", f"{float(row['Günlük Değişim TL']):+.2f} TL")
    c7.metric("Hacim", f"{float(row['Hacim']):,.0f}")
    c8.metric("Veri tarihi", str(row["Veri Tarihi"]))


def _render_result(result: BistDailyMarketResult, selected_display: str) -> None:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Evren", result.evren_adi)
    m2.metric("Evren sembolü", result.evren_sembol_sayisi)
    m3.metric("Verisi hazır", result.veri_hazir)
    m4.metric("Veri hatası", result.veri_hatasi)

    st.caption(
        f"Evren kaynağı: {result.evren_kaynagi} · "
        f"Evren tarihi: {result.evren_tarihi} · "
        f"Veri kaynak sırası: {', '.join(result.kaynak_sirasi)}"
    )

    if result.tablo.empty:
        st.warning("Gösterilebilir günlük piyasa verisi bulunamadı.")
        return

    query = st.text_input(
        "Listede hisse ara",
        placeholder="Örn. THYAO",
        key=f"bist_daily_market_symbol_query::{selected_display}",
    ).strip().upper().removesuffix(".IS")

    if query:
        matches = result.tablo[result.tablo["Hisse"].astype(str).str.upper() == query]
        if matches.empty:
            st.warning(f"{query} mevcut günlük listede bulunamadı.")
        else:
            _single_stock_card(matches.iloc[0])

    st.subheader(f"{selected_display} Günlük Değişim Listesi")
    only = st.radio(
        "Görünüm",
        ("Tümü", "Yükselenler", "Düşenler"),
        horizontal=True,
        key=f"bist_daily_market_filter::{selected_display}",
    )

    table = result.tablo.copy()
    if only == "Yükselenler":
        table = table[table["Günlük Değişim %"] > 0]
    elif only == "Düşenler":
        table = table[table["Günlük Değişim %"] < 0]

    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            "Son Fiyat": st.column_config.NumberColumn(format="%.2f"),
            "Günlük Değişim %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Günlük Değişim TL": st.column_config.NumberColumn(format="%+.2f"),
            "Açılış": st.column_config.NumberColumn(format="%.2f"),
            "En Düşük": st.column_config.NumberColumn(format="%.2f"),
            "En Yüksek": st.column_config.NumberColumn(format="%.2f"),
            "Önceki Kapanış": st.column_config.NumberColumn(format="%.2f"),
            "Hacim": st.column_config.NumberColumn(format="%.0f"),
        },
    )

    if result.hatalar:
        with st.expander("Veri hataları"):
            st.dataframe(
                pd.DataFrame(
                    [{"Hisse": h.sembol.removesuffix(".IS"), "Hata": h.hata} for h in result.hatalar]
                ),
                hide_index=True,
                width="stretch",
            )


def _render_custom_list() -> None:
    st.subheader("Özel Liste")
    st.caption(
        "Bir veya birden fazla hisseyi tam kodla ya da kısa kodla yazabilirsiniz. "
        "Örnek: THY, TUPR, ASEL veya THYAO, TUPRS, ASELS. "
        "Birden fazla sonuç varsa seçim yapmanız istenir."
    )

    raw = st.text_area(
        "Hisseler",
        placeholder="THY, TUPR, ASEL\nveya\nTHYAO TUPRS ASELS",
        key="bist_daily_market_custom_input",
        height=100,
    )

    tokens = ozel_liste_girdilerini_ayir(raw)
    if not tokens:
        st.info("Özel liste için en az bir hisse kodu veya kısa kod yazın.")
        return

    try:
        _, universe_symbols = bist_tum_sembollerini_yukle(internetten_guncelle=False)
        company_names = bist_tum_sirket_adlarini_yukle()
    except Exception as exc:
        st.error(f"BIST Tüm sembol listesi yüklenemedi: {exc}")
        return

    # V11_TRACK4_COMPANY_NAME_MATCHING
    resolved: list[str] = []
    unresolved: list[str] = []

    for token in tokens:
        matches = sembol_eslesmeleri(token, universe_symbols, company_names=company_names)
        if not matches:
            unresolved.append(token)
            continue

        if len(matches) == 1:
            chosen = matches[0]
            st.caption(f"{token} → {chosen}")
        else:
            chosen = st.selectbox(
                f"{token} için eşleşme",
                matches,
                key=f"bist_daily_market_custom_match::{token}",
            )
        if chosen not in resolved:
            resolved.append(chosen)

    if unresolved:
        st.warning("Tanımlanamayan girişler: " + ", ".join(unresolved))

    if not resolved:
        return

    run = st.button(
        "Özel Liste Değerlerini Getir",
        type="primary",
        width="stretch",
        key="bist_daily_market_custom_run",
    )

    cache_key = "bist_daily_market_custom_last_result"
    if run:
        try:
            with st.spinner("Özel liste günlük verileri yükleniyor..."):
                result = bist_ozel_liste_olustur(resolved, internetten_guncelle=False)
        except Exception as exc:
            st.error(f"Özel liste yüklenemedi: {exc}")
            return
        st.session_state[cache_key] = result
    else:
        result = st.session_state.get(cache_key)

    if result is None:
        return

    _render_result(result, "Özel Liste")


def render_bist_daily_market() -> None:
    st.header("BIST Günlük Piyasa")
    st.caption(
        "BIST Tüm, XU100, XU50, XU30 ve Özel Liste için son tamamlanmış günlük OHLCV verisini gösterir. "
        "Son fiyat, günlük değişim, açılış, en düşük, en yüksek, önceki kapanış ve hacim "
        "aynı mevcut batch veri hattından üretilir."
    )

    display_to_universe = {
        "BIST Tüm": "BIST Tüm",
        "XU100": "BIST 100",
        "XU50": "BIST 50",
        "XU30": "BIST 30",
        "Özel Liste": None,
    }
    selected_display = st.radio(
        "Piyasa içeriği",
        tuple(display_to_universe),
        horizontal=True,
        key="bist_daily_market_universe",
    )

    if selected_display == "Özel Liste":
        _render_custom_list()
        return

    selected_universe = display_to_universe[selected_display]
    st.subheader(selected_display)

    run = st.button(
        f"{selected_display} Günlük Listeyi Getir",
        type="primary",
        width="stretch",
        key=f"bist_daily_market_run::{selected_display}",
    )

    cache_key = f"bist_daily_market_last_result::{selected_universe}"
    if run:
        try:
            with st.spinner(f"{selected_display} günlük verileri yükleniyor..."):
                result = bist_gunluk_piyasa_olustur(
                    evren_adi=selected_universe,
                    internetten_guncelle=False,
                )
        except Exception as exc:
            st.error(f"BIST Günlük Piyasa yüklenemedi: {exc}")
            return
        st.session_state[cache_key] = result
    else:
        result = st.session_state.get(cache_key)

    if result is None:
        st.info(f"{selected_display} günlük listesini görmek için yukarıdaki düğmeye basın.")
        return

    _render_result(result, selected_display)
