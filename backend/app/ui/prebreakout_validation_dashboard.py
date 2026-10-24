from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

from backend.app.prebreakout.prebreakout_validation import (
    PreBreakoutValidationConfig,
    dogrulama_ozeti,
    toplu_tarihsel_dogrulama,
)
from backend.app.prebreakout.prebreakout_validation_report import (
    asama_bazli_ozet,
    dogrulama_kayitlarini_tabloya_cevir,
    dogrulama_ozetini_tabloya_cevir,
)
from backend.app.prebreakout.prebreakout_score_threshold_calibration import (
    ThresholdCalibrationConfig,
    calibration_thresholds,
    filter_records_for_threshold,
    generate_calibration_report,
)
from backend.app.prebreakout.prebreakout_universe import (
    ON_YUKSELIS_EVRENLERI,
    OZEL_LISTE,
    SONUC_LIMITLERI,
    on_yukselis_evrenini_yukle,
    sembolleri_hazirla,
    sonuc_limitini_kesim_bazinda_uygula,
)


DEFAULT_SYMBOLS = "THYAO, ASELS, TUPRS, SAHOL, KCHOL"


def _tek_sembol_verisi_indir(
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

    required = ["Open", "High", "Low", "Close", "Volume"]
    if any(column not in data.columns for column in required):
        return pd.DataFrame()

    result = data.loc[:, required].copy()
    result.index = pd.to_datetime(result.index).tz_localize(None)
    return result.dropna().sort_index()


def _etiket_dagilimi_table(records_table: pd.DataFrame) -> pd.DataFrame:
    if records_table.empty:
        return pd.DataFrame(columns=["Performans etiketi", "Adet"])

    counts = (
        records_table["performance_label"]
        .value_counts(dropna=False)
        .rename_axis("Performans etiketi")
        .reset_index(name="Adet")
    )
    return counts


def on_yukselis_toplu_dogrulama_formu() -> None:
    st.header("Ön Yükseliş Toplu Tarihsel Doğrulama")
    st.caption(
        "Ön Yükseliş Hazırlık Motorunu çok sayıda kesim tarihinde doğrular. "
        "Kesim sonrası fiyatlar aday üretiminde kullanılmaz; yalnızca ileri "
        "performans ölçümünde kullanılır."
    )

    with st.sidebar:
        st.subheader("Toplu doğrulama ayarları")

        universe_name = st.selectbox(
            "Evren",
            options=ON_YUKSELIS_EVRENLERI,
            index=ON_YUKSELIS_EVRENLERI.index(OZEL_LISTE),
            key="prebreakout_validation_universe",
        )
        raw_symbols = DEFAULT_SYMBOLS
        if universe_name == OZEL_LISTE:
            raw_symbols = st.text_area(
                "Hisse listesi",
                value=DEFAULT_SYMBOLS,
                height=120,
                key="prebreakout_validation_symbols",
            )
        result_limit = st.selectbox(
            "Her kesimde gösterilecek sonuç",
            options=SONUC_LIMITLERI,
            index=1,
            key="prebreakout_validation_result_limit",
        )

        default_end = date.today() - timedelta(days=30)
        default_start = default_end - timedelta(days=180)

        start_date = st.date_input(
            "Başlangıç tarihi",
            value=default_start,
            max_value=date.today(),
            key="prebreakout_validation_start",
        )
        end_date = st.date_input(
            "Bitiş tarihi",
            value=default_end,
            max_value=date.today(),
            key="prebreakout_validation_end",
        )
        cutoff_step = st.number_input(
            "Kesim adımı (işlem günü)",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
            key="prebreakout_validation_step",
        )
        minimum_score = st.slider(
            "Minimum hazırlık skoru",
            min_value=0,
            max_value=100,
            value=45,
            step=1,
            key="prebreakout_validation_score",
        )

    if universe_name == OZEL_LISTE and not sembolleri_hazirla(raw_symbols):
        st.warning("En az bir hisse sembolü girin.")
        return

    if start_date > end_date:
        st.error("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
        return

    if not st.button(
        "Toplu tarihsel doğrulamayı başlat",
        type="primary",
        width="stretch",
        key="prebreakout_validation_run",
    ):
        return

    try:
        universe = on_yukselis_evrenini_yukle(
            universe_name,
            raw_symbols,
        )
    except Exception as error:
        st.error(f"Evren yüklenemedi: {error}")
        return

    symbols = universe.semboller
    st.caption(
        f"Evren: {universe.ad} · {len(symbols)} sembol · "
        f"Kaynak: {universe.kaynak} · Tarih: {universe.tarih}"
    )

    history_start = start_date - timedelta(days=550)
    history_end = end_date + timedelta(days=45)

    data_by_symbol: dict[str, pd.DataFrame] = {}
    errors: list[str] = []

    with st.spinner("Tarihsel fiyat verileri indiriliyor..."):
        for symbol in symbols:
            try:
                data = _tek_sembol_verisi_indir(
                    symbol,
                    start_date=history_start,
                    end_date=history_end,
                )
                if data.empty:
                    errors.append(f"{symbol}: fiyat verisi bulunamadı.")
                    continue
                data_by_symbol[symbol] = data
            except Exception as error:
                errors.append(f"{symbol}: {error}")

    if errors:
        with st.expander("Veri indirme hataları", expanded=False):
            for error in errors:
                st.write(f"• {error}")

    if not data_by_symbol:
        st.error("Doğrulama için kullanılabilir veri bulunamadı.")
        return

    calibration_config = ThresholdCalibrationConfig(
        current_threshold=int(minimum_score),
        alternative_thresholds=tuple(
            sorted(
                {
                    max(0, int(minimum_score) - 10),
                    max(0, int(minimum_score) - 5),
                    min(100, int(minimum_score) + 5),
                    min(100, int(minimum_score) + 10),
                }
            )
        ),
        minimum_sample_size=10,
    )
    validation_config = PreBreakoutValidationConfig(
        start_date=start_date,
        end_date=end_date,
        cutoff_step=int(cutoff_step),
        minimum_score=min(calibration_thresholds(calibration_config)),
    )

    with st.spinner("Kesim tarihleri ve ileri performanslar hesaplanıyor..."):
        records = toplu_tarihsel_dogrulama(
            data_by_symbol,
            validation_config,
        )

    all_records_table = dogrulama_kayitlarini_tabloya_cevir(records)
    calibration_report = generate_calibration_report(
        all_records_table,
        calibration_config,
    )
    current_records = filter_records_for_threshold(
        records,
        int(minimum_score),
    )
    summary = dogrulama_ozeti(current_records)
    records_table = dogrulama_kayitlarini_tabloya_cevir(current_records)
    summary_table = dogrulama_ozetini_tabloya_cevir(summary)
    stage_table = asama_bazli_ozet(records)
    label_table = _etiket_dagilimi_table(records_table)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam kesim", summary.total_replays)
    c2.metric("Aday", summary.accepted_candidates)
    c3.metric("Başarı oranı", f"%{summary.success_rate_pct:.1f}")
    c4.metric(
        "Yanlış pozitif oranı",
        f"%{summary.false_positive_rate_pct:.1f}",
    )

    st.subheader("Eşik kalibrasyon önerisi")
    from backend.app.prebreakout.prebreakout_validation_evidence import persist_prebreakout_validation_evidence
    persist_prebreakout_validation_evidence(records)
    recommendation = calibration_report.recommendation
    st.info(
        f"{recommendation.decision}: mevcut eşik "
        f"{recommendation.current_threshold}, önerilen eşik "
        f"{recommendation.recommended_threshold}. {recommendation.reason}"
    )
    st.caption(
        "Bu rapor yalnızca karşılaştırma ve karar desteği üretir. "
        f"Otomatik eşik değişikliği: "
        f"{recommendation.automatic_change_applied}."
    )
    st.dataframe(
        calibration_report.comparison,
        hide_index=True,
        width="stretch",
    )
    st.download_button(
        "Kalibrasyon önerisini CSV indir",
        data=calibration_report.comparison.to_csv(index=False).encode(
            "utf-8-sig"
        ),
        file_name="Hisse-Robotu-On-Yukselis-Esik-Kalibrasyonu.csv",
        mime="text/csv",
        width="stretch",
        key="prebreakout_calibration_csv",
    )

    st.subheader("Performans etiketi dağılımı")
    st.dataframe(label_table, hide_index=True, width="stretch")

    st.subheader("Aşama bazlı performans")
    st.dataframe(stage_table, hide_index=True, width="stretch")

    st.subheader("Ayrıntılı tarihsel kayıtlar")
    if records_table.empty:
        st.info(
            "Seçilen tarih aralığı ve minimum skorla doğrulama kaydı oluşmadı."
        )
    else:
        display_table = records_table.sort_values(
            by=["cutoff_date", "score", "symbol"],
            ascending=[False, False, True],
        )
        display_table = sonuc_limitini_kesim_bazinda_uygula(
            display_table,
            result_limit,
        )
        display_table.insert(0, "Evren tarihi", universe.tarih)
        display_table.insert(0, "Evren kaynağı", universe.kaynak)
        display_table.insert(0, "Evren", universe.ad)
        st.dataframe(display_table, hide_index=True, width="stretch")

        st.download_button(
            "Ayrıntılı sonuçları CSV indir",
            data=display_table.to_csv(index=False).encode("utf-8-sig"),
            file_name="Hisse-Robotu-On-Yukselis-Toplu-Dogrulama.csv",
            mime="text/csv",
            width="stretch",
            key="prebreakout_validation_csv",
        )

    st.download_button(
        "Özet sonucu CSV indir",
        data=summary_table.to_csv(index=False).encode("utf-8-sig"),
        file_name="Hisse-Robotu-On-Yukselis-Toplu-Dogrulama-Ozet.csv",
        mime="text/csv",
        width="stretch",
        key="prebreakout_validation_summary_csv",
    )
