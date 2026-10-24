from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

from backend.app.prebreakout.prebreakout_backtest import (
    HORIZONS,
    PreBreakoutReplayResult,
    performans_etiketi_belirle,
    tarihsel_yeniden_oynat,
)
from backend.app.prebreakout.prebreakout_engine import (
    on_yukselis_hazirligini_analiz_et,
)
from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutConfig,
    PreBreakoutResult,
)


DEFAULT_SYMBOLS = "THYAO, ASELS, TUPRS, SAHOL, KCHOL"


def sembolleri_hazirla(raw: str) -> tuple[str, ...]:
    symbols: list[str] = []
    seen: set[str] = set()

    for item in raw.replace("\n", ",").split(","):
        symbol = item.strip().upper()
        if not symbol:
            continue
        if not symbol.endswith(".IS"):
            symbol = f"{symbol}.IS"
        if symbol not in seen:
            symbols.append(symbol)
            seen.add(symbol)

    return tuple(symbols)


def _download_single_symbol(
    symbol: str,
    *,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    data = yf.download(
        symbol,
        start=start_date.isoformat(),
        end=(end_date + timedelta(days=1)).isoformat(),
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if data is None or data.empty:
        return pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        if symbol in data.columns.get_level_values(-1):
            data = data.xs(symbol, axis=1, level=-1, drop_level=True)
        elif symbol in data.columns.get_level_values(0):
            data = data.xs(symbol, axis=1, level=0, drop_level=True)

    expected = ["Open", "High", "Low", "Close", "Volume"]
    missing = [column for column in expected if column not in data.columns]
    if missing:
        return pd.DataFrame()

    result = data.loc[:, expected].copy()
    result.index = pd.to_datetime(result.index).tz_localize(None)
    return result.dropna().sort_index()


def guncel_sonuc_satiri(result: PreBreakoutResult) -> dict[str, object]:
    features = result.features
    return {
        "Hisse": result.symbol.removesuffix(".IS"),
        "Hazırlık skoru": result.score,
        "Aşama": result.stage.value,
        "Aşama açıklaması": result.stage_label,
        "Aday": result.accepted,
        "Geç giriş": result.late_entry,
        "Kapanış": None if features is None else round(features.close, 4),
        "Dirence uzaklık %": None if features is None else round(features.direnc_uzaklik_pct, 2),
        "RSI14": None if features is None else round(features.rsi14, 2),
        "MACD histogram eğimi": None if features is None else round(features.macd_histogram_egimi, 4),
        "Hacim 3/10": None if features is None else round(features.hacim_orani_3_10, 2),
        "ATR daralma": None if features is None else round(features.atr_daralma_orani, 2),
        "Son gün %": None if features is None else round(features.son_gun_getirisi_pct, 2),
        "Risk/ödül": None if features is None else round(features.risk_odul, 2),
        "Olumlu işaretler": " · ".join(result.reasons),
        "Riskler": " · ".join(result.risks),
    }


def replay_sonuc_satiri(result: PreBreakoutReplayResult) -> dict[str, object]:
    row = guncel_sonuc_satiri(result.analysis)
    row["Kesim tarihi"] = result.cutoff_date.isoformat()
    row["Performans etiketi"] = performans_etiketi_belirle(result)
    row["Giriş kapanışı"] = result.entry_close

    for performance in result.forward:
        suffix = f"{performance.horizon}G"
        row[f"{suffix} kapanış %"] = None if performance.close_return_pct is None else round(performance.close_return_pct, 2)
        row[f"{suffix} en yüksek %"] = None if performance.max_return_pct is None else round(performance.max_return_pct, 2)
        row[f"{suffix} en düşük %"] = None if performance.min_return_pct is None else round(performance.min_return_pct, 2)

    return row


def _render_result_detail(result: PreBreakoutResult) -> None:
    st.subheader(
        f"{result.symbol.removesuffix('.IS')} · "
        f"{result.score}/100 · {result.stage_label}"
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**Olumlu hazırlık işaretleri**")
        if result.reasons:
            for reason in result.reasons:
                st.write(f"• {reason}")
        else:
            st.caption("Belirgin olumlu hazırlık işareti bulunamadı.")

    with right:
        st.markdown("**Riskler ve eksik teyitler**")
        if result.risks:
            for risk in result.risks:
                st.write(f"• {risk}")
        else:
            st.caption("Ek risk uyarısı bulunmuyor.")


def on_yukselis_hazirlik_formu() -> None:
    st.header("Ön Yükseliş Hazırlık Taraması")
    st.caption(
        "Yükseliş hareketi başlamadan önce sıkışma, momentum hazırlığı, "
        "hacim birikimi ve dirence yakınlık işaretlerini araştırır. "
        "Kesin alım sinyali üretmez."
    )

    with st.sidebar:
        st.subheader("Ön yükseliş ayarları")
        mode = st.radio(
            "Çalışma türü",
            options=("Güncel hazırlık", "Tarihsel yeniden oynatma"),
            key="prebreakout_mode",
        )
        raw_symbols = st.text_area(
            "Hisse listesi",
            value=DEFAULT_SYMBOLS,
            height=110,
            key="prebreakout_symbols",
        )
        minimum_score = st.slider(
            "Minimum gösterim skoru",
            min_value=0,
            max_value=100,
            value=45,
            step=1,
            key="prebreakout_minimum_score",
        )
        maximum_daily_return = st.number_input(
            "Maksimum son gün primi (%)",
            min_value=0.5,
            max_value=15.0,
            value=4.0,
            step=0.5,
            key="prebreakout_max_daily_return",
        )
        cutoff_date = None
        if mode == "Tarihsel yeniden oynatma":
            cutoff_date = st.date_input(
                "Kesim tarihi",
                value=date.today() - timedelta(days=30),
                max_value=date.today(),
                key="prebreakout_cutoff_date",
            )

    symbols = sembolleri_hazirla(raw_symbols)
    if not symbols:
        st.warning("En az bir hisse sembolü girin.")
        return

    config = PreBreakoutConfig(
        maksimum_son_gun_getirisi_pct=float(maximum_daily_return)
    )

    if not st.button(
        "Ön yükseliş taramasını başlat",
        type="primary",
        width="stretch",
        key="prebreakout_run",
    ):
        return

    rows: list[dict[str, object]] = []
    details: list[PreBreakoutResult] = []
    errors: list[str] = []

    with st.spinner("Günlük fiyat verileri ve hazırlık özellikleri hesaplanıyor..."):
        for symbol in symbols:
            try:
                if mode == "Tarihsel yeniden oynatma":
                    assert cutoff_date is not None
                    data = _download_single_symbol(
                        symbol,
                        start_date=cutoff_date - timedelta(days=550),
                        end_date=cutoff_date + timedelta(days=45),
                    )
                    if data.empty:
                        errors.append(f"{symbol}: fiyat verisi bulunamadı.")
                        continue

                    replay = tarihsel_yeniden_oynat(
                        symbol,
                        data,
                        cutoff_date,
                        config=config,
                        horizons=HORIZONS,
                    )
                    if replay.analysis.score >= minimum_score:
                        rows.append(replay_sonuc_satiri(replay))
                        details.append(replay.analysis)
                else:
                    end_date = date.today()
                    data = _download_single_symbol(
                        symbol,
                        start_date=end_date - timedelta(days=550),
                        end_date=end_date,
                    )
                    if data.empty:
                        errors.append(f"{symbol}: fiyat verisi bulunamadı.")
                        continue

                    result = on_yukselis_hazirligini_analiz_et(
                        symbol,
                        data,
                        config=config,
                    )
                    if result.score >= minimum_score:
                        rows.append(guncel_sonuc_satiri(result))
                        details.append(result)
            except Exception as error:
                errors.append(f"{symbol}: {error}")

    if errors:
        with st.expander("Veri veya analiz hataları", expanded=False):
            for error in errors:
                st.write(f"• {error}")

    if not rows:
        st.info("Seçilen koşullarda gösterilecek ön yükseliş adayı bulunamadı.")
        return

    table = pd.DataFrame(rows).sort_values(
        by=["Hazırlık skoru", "Hisse"],
        ascending=[False, True],
    )
    st.success(
        f"{len(symbols)} sembol incelendi; "
        f"{len(table)} sonuç minimum gösterim skorunu geçti."
    )
    st.dataframe(table, hide_index=True, width="stretch")

    st.download_button(
        "Sonuçları CSV indir",
        data=table.to_csv(index=False).encode("utf-8-sig"),
        file_name="Hisse-Robotu-On-Yukselis-Hazirlik.csv",
        mime="text/csv",
        width="stretch",
        key="prebreakout_csv",
    )

    if details:
        options = {
            f"{item.symbol.removesuffix('.IS')} · "
            f"{item.score}/100 · {item.stage_label}": item
            for item in details
        }
        selected = st.selectbox(
            "Aday ayrıntısı",
            options=tuple(options),
            key="prebreakout_detail",
        )
        _render_result_detail(options[selected])
