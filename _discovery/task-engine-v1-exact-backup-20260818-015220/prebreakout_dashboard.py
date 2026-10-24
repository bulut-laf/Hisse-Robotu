from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf

from backend.app.prebreakout.prebreakout_backtest import (
    HORIZONS,
    PreBreakoutReplayResult,
    performans_etiketi_belirle,
    tarihsel_yeniden_oynat,
)
from backend.app.prebreakout.prebreakout_calibration import (
    asama_guven_araliklarini_hesapla,
    asama_guven_araliklarini_tabloya_cevir,
    asama_kalibrasyonunu_hesapla,
    asama_kalibrasyonunu_tabloya_cevir,
    guvenilir_asama_satirlarini_sec,
    kalibrasyon_ozetini_hesapla,
    kalibrasyon_esik_onerilerini_hesapla,
    kalibrasyon_esik_onerilerini_tabloya_cevir,
    esik_onerilerini_tarihsel_dogrula,
    esik_dogrulamalarini_tabloya_cevir,
    lider_duyarlilik_senaryolarini_hesapla,
    lider_duyarlilik_senaryolarini_tabloya_cevir,
    lider_kararlilik_ozetini_hesapla,
    momentum_kalibrasyonunu_hesapla,
    momentum_kalibrasyonunu_tabloya_cevir,
    temkinli_lider_asamayi_sec,
)
from backend.app.prebreakout.prebreakout_live_watch import (
    DEFAULT_LIVE_WATCH_PATH,
    canli_sinyalleri_kaydet,
    canli_sinyalleri_yukle,
)
from backend.app.prebreakout.prebreakout_candidate_lifecycle import (
    CandidateLifecycleConfig,
    CandidatePriceObservation,
    adayin_yasam_dongusunu_degerlendir,
    yasam_dongusu_ozeti,
)
from backend.app.prebreakout.prebreakout_live_performance import (
    canli_performans_ozeti,
    canli_sinyal_performansini_hesapla,
)
from backend.app.prebreakout.prebreakout_performance_comparison import (
    performans_karsilastirmasini_hesapla,
    performans_karsilastirmasini_tabloya_cevir,
)
from backend.app.prebreakout.prebreakout_paper_portfolio import (
    PaperPortfolioConfig,
    deneme_islemini_hesapla,
    deneme_portfoyu_ozeti,
    deneme_portfoyunu_tabloya_cevir,
)
from backend.app.prebreakout.prebreakout_release_readiness import (
    on_yukselis_surum_hazirligini_degerlendir,
    surum_hazirligini_tabloya_cevir,
)
from backend.app.prebreakout.prebreakout_operational_health import (
    operasyon_sagligini_degerlendir,
    operasyon_sagligini_tabloya_cevir,
)
from backend.app.prebreakout.prebreakout_real_result_evaluation import (
    gercek_sonuclari_degerlendir,
    gercek_sonuc_asama_tablosu,
    gercek_sonuc_esik_tablosu,
)
from backend.app.prebreakout.prebreakout_threshold_policy import mevcut_esik_politikasi
from backend.app.prebreakout.prebreakout_daily_operation import (
    DailyOperationStatus,
    gunluk_operasyon_durumunu_yukle,
)
from backend.app.prebreakout.prebreakout_operation_archive import (
    gunluk_operasyon_arsivini_tabloya_cevir,
    gunluk_operasyon_arsivini_yukle,
    gunluk_operasyon_karsilastirmasi,
    yonetici_ozeti_olustur,
)
from backend.app.prebreakout.prebreakout_operation_alerts import (
    OperationTrendAlarmLevel,
    gunluk_yonetici_ozetini_hesapla,
    operasyon_alarmlarini_tabloya_cevir,
)
from backend.app.prebreakout.prebreakout_alarm_journal import (
    alarm_gecmisini_tabloya_cevir,
    alarm_gecmisini_yukle,
    karar_gunlugunu_tabloya_cevir,
    karar_gunlugunu_yukle,
)
from backend.app.prebreakout.prebreakout_engine import (
    on_yukselis_hazirligini_analiz_et,
)
from backend.app.prebreakout.prebreakout_models import (
    PreBreakoutConfig,
    PreBreakoutResult,
)
from backend.app.prebreakout.prebreakout_universe import (
    ON_YUKSELIS_EVRENLERI,
    OZEL_LISTE,
    SONUC_LIMITLERI,
    on_yukselis_evrenini_yukle,
    sembolleri_hazirla,
    sonuc_limitini_uygula,
)


DEFAULT_SYMBOLS = "THYAO, ASELS, TUPRS, SAHOL, KCHOL"


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
        universe_name = st.selectbox(
            "Evren",
            options=ON_YUKSELIS_EVRENLERI,
            index=ON_YUKSELIS_EVRENLERI.index(OZEL_LISTE),
            key="prebreakout_universe",
        )
        raw_symbols = DEFAULT_SYMBOLS
        if universe_name == OZEL_LISTE:
            raw_symbols = st.text_area(
                "Hisse listesi",
                value=DEFAULT_SYMBOLS,
                height=110,
                key="prebreakout_symbols",
            )
        result_limit = st.selectbox(
            "Gösterilecek sonuç",
            options=SONUC_LIMITLERI,
            index=1,
            key="prebreakout_result_limit",
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

    if universe_name == OZEL_LISTE and not sembolleri_hazirla(raw_symbols):
        st.warning("En az bir hisse sembolü girin.")
        return

    config = PreBreakoutConfig(
        maksimum_son_gun_getirisi_pct=float(maximum_daily_return)
    )

    run_requested = st.button(
        "Ön yükseliş taramasını başlat",
        type="primary",
        width="stretch",
        key="prebreakout_run",
    )

    run_signature = (
        mode,
        universe_name,
        raw_symbols if universe_name == OZEL_LISTE else "",
        int(minimum_score),
        float(maximum_daily_return),
        None if cutoff_date is None else cutoff_date.isoformat(),
    )
    cache_key = "prebreakout_last_completed_run"
    cached_run = st.session_state.get(cache_key)

    if not run_requested:
        if (
            not isinstance(cached_run, dict)
            or cached_run.get("signature") != run_signature
        ):
            return

        rows = list(cached_run["rows"])
        details = list(cached_run["details"])
        replay_results = list(cached_run["replay_results"])
        errors = list(cached_run["errors"])
        symbols = tuple(cached_run["symbols"])
        universe_source = str(cached_run["universe_source"])
        universe_date = str(cached_run["universe_date"])
    else:
        try:
            universe = on_yukselis_evrenini_yukle(
                universe_name,
                raw_symbols,
            )
        except Exception as error:
            st.error(f"Evren yüklenemedi: {error}")
            return

        symbols = universe.semboller
        universe_source = universe.kaynak
        universe_date = universe.tarih
        rows: list[dict[str, object]] = []
        details: list[PreBreakoutResult] = []
        replay_results: list[PreBreakoutReplayResult] = []
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
                            replay_results.append(replay)
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

        st.session_state[cache_key] = {
            "signature": run_signature,
            "rows": tuple(rows),
            "details": tuple(details),
            "replay_results": tuple(replay_results),
            "errors": tuple(errors),
            "symbols": symbols,
            "universe_source": universe_source,
            "universe_date": universe_date,
        }

    if errors:
        with st.expander("Veri veya analiz hataları", expanded=False):
            for error in errors:
                st.write(f"• {error}")

    if not rows:
        st.info("Seçilen koşullarda gösterilecek ön yükseliş adayı bulunamadı.")
        return

    full_table = pd.DataFrame(rows).sort_values(
        by=["Hazırlık skoru", "Hisse"],
        ascending=[False, True],
    )
    full_table.insert(0, "Evren tarihi", universe_date)
    full_table.insert(0, "Evren kaynağı", universe_source)
    full_table.insert(0, "Evren", universe_name)
    table = sonuc_limitini_uygula(full_table, result_limit)
    st.success(
        f"{len(symbols)} sembol incelendi; "
        f"{len(full_table)} sonuç minimum gösterim skorunu geçti; "
        f"{len(table)} sonuç gösteriliyor."
    )
    st.caption(
        f"Evren kaynağı: {universe_source} · Evren tarihi: {universe_date}"
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

    if mode == "Güncel hazırlık":
        st.subheader("Canlı İzleme Portföyü")
        st.caption(
            "E2–E4 sinyalleri kayıt anındaki fiyat, aşama, özellikler ve eşik "
            "politikasıyla değiştirilemez günlük kayda eklenir."
        )
        live_watch_path = Path(DEFAULT_LIVE_WATCH_PATH)
        existing_live_signals = canli_sinyalleri_yukle(live_watch_path)
        st.metric("Toplam canlı sinyal kaydı", len(existing_live_signals))
        if st.button(
            "E2–E4 adaylarını canlı izlemeye kaydet",
            width="stretch",
            key="prebreakout_live_watch_save",
        ):
            saved_signals = canli_sinyalleri_kaydet(
                details,
                date.today(),
                mevcut_esik_politikasi(),
                path=live_watch_path,
            )
            if saved_signals:
                st.success(f"{len(saved_signals)} yeni sinyal canlı izlemeye kaydedildi.")
            else:
                st.info("Yeni E2–E4 sinyali yok veya bugünkü kayıtlar zaten mevcut.")

        if existing_live_signals:
            _render_daily_operations_hub(existing_live_signals)

            st.markdown("Aday yaşam döngüsü")
            st.caption(
                "Hazırlık, tetiklenme, başarısızlık ve süresi doldu durumları "
                "sinyal gününden sonraki fiyatlarla değerlendirilir."
            )
            lifecycle_records = []
            for signal in existing_live_signals:
                start_day = date.fromisoformat(signal.signal_date)
                price_data = _download_single_symbol(
                    signal.symbol,
                    start_date=start_day,
                    end_date=date.today(),
                )
                observations = tuple(
                    CandidatePriceObservation(
                        observation_date=index.date(),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                    )
                    for index, row in price_data.iterrows()
                    if index.date() > start_day
                )
                lifecycle_records.append(
                    adayin_yasam_dongusunu_degerlendir(
                        signal,
                        observations,
                        config=CandidateLifecycleConfig(),
                        as_of_date=date.today(),
                    )
                )
            lifecycle_summary = yasam_dongusu_ozeti(lifecycle_records)
            life_left, life_middle, life_right = st.columns(3)
            life_left.metric("Hazırlıkta", lifecycle_summary["HAZIRLIK"])
            life_middle.metric("Tetiklendi", lifecycle_summary["TETIKLENDI"])
            life_right.metric(
                "Başarısız / süresi doldu",
                lifecycle_summary["BASARISIZ"] + lifecycle_summary["SURESI_DOLDU"],
            )
            lifecycle_table = pd.DataFrame(
                [
                    {
                        "Hisse": record.symbol.removesuffix(".IS"),
                        "Sinyal tarihi": record.signal_date,
                        "Aşama": record.signal_stage,
                        "Durum": record.status.value,
                        "Durum tarihi": record.status_date,
                        "Geçen gün": record.elapsed_calendar_days,
                        "İşlem günü": record.observed_session_count,
                        "En yüksek %": None if record.max_return_pct is None else round(record.max_return_pct, 2),
                        "En düşük %": None if record.min_return_pct is None else round(record.min_return_pct, 2),
                        "Not": record.note,
                    }
                    for record in lifecycle_records
                ]
            )
            st.dataframe(lifecycle_table, hide_index=True, width="stretch")

            st.markdown("Gerçek sonuç takibi")
            st.caption(
                "Canlı sinyallerin 5/10/20 işlem günlük kapanış getirileri, "
                "dönem içi en yüksek/en düşük hareketleri ve maksimum geri çekilmesi ölçülür."
            )
            performance_records = []
            for signal in existing_live_signals:
                start_day = date.fromisoformat(signal.signal_date)
                price_data = _download_single_symbol(
                    signal.symbol,
                    start_date=start_day,
                    end_date=date.today(),
                )
                observations = tuple(
                    CandidatePriceObservation(
                        observation_date=index.date(),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                    )
                    for index, row in price_data.iterrows()
                    if index.date() > start_day
                )
                performance_records.append(
                    canli_sinyal_performansini_hesapla(
                        signal,
                        observations,
                        as_of_date=date.today(),
                    )
                )

            performance_summary = canli_performans_ozeti(performance_records)
            perf_left, perf_middle, perf_right = st.columns(3)
            perf_left.metric("Ölçülen sonuç", performance_summary["ÖLÇÜLEN"])
            perf_middle.metric("Başarılı", performance_summary["Başarılı"])
            perf_right.metric("Ölçülemiyor", performance_summary["Ölçülemiyor"])

            performance_table_rows = []
            for record in performance_records:
                row = {
                    "Hisse": record.symbol.removesuffix(".IS"),
                    "Sinyal tarihi": record.signal_date,
                    "Aşama": record.signal_stage,
                    "Sonuç etiketi": record.label.value,
                    "Mevcut işlem günü": record.available_session_count,
                    "Giriş kapanışı": round(record.entry_close, 4),
                    "Not": record.note,
                }
                for horizon in record.horizons:
                    suffix = f"{horizon.horizon}G"
                    row[f"{suffix} kapanış %"] = None if horizon.close_return_pct is None else round(horizon.close_return_pct, 2)
                    row[f"{suffix} en yüksek %"] = None if horizon.max_return_pct is None else round(horizon.max_return_pct, 2)
                    row[f"{suffix} en düşük %"] = None if horizon.min_return_pct is None else round(horizon.min_return_pct, 2)
                    row[f"{suffix} maksimum geri çekilme %"] = None if horizon.max_drawdown_pct is None else round(horizon.max_drawdown_pct, 2)
                performance_table_rows.append(row)

            performance_table = pd.DataFrame(performance_table_rows)
            st.dataframe(performance_table, hide_index=True, width="stretch")
            st.download_button(
                "Canlı sonuçları CSV indir",
                data=performance_table.to_csv(index=False).encode("utf-8-sig"),
                file_name="Hisse-Robotu-On-Yukselis-Canli-Sonuclar.csv",
                mime="text/csv",
                width="stretch",
                key="prebreakout_live_performance_csv",
            )

            _render_paper_portfolio(existing_live_signals)
            _render_operational_health(
                existing_live_signals,
                lifecycle_records,
                performance_records,
            )
            _render_real_result_evaluation(
                existing_live_signals,
                lifecycle_records,
                performance_records,
            )

    if mode == "Tarihsel yeniden oynatma" and replay_results:
        st.subheader("Ön Yükseliş Kalibrasyonu")
        st.caption(
            "Aşama ve momentum kırılımları yalnızca raporlama amacıyla "
            "hesaplanır; üretim eşikleri otomatik değiştirilmez."
        )

        stage_rows = asama_kalibrasyonunu_hesapla(replay_results)
        minimum_sample_size = st.number_input(
            "Güvenilir aşama için minimum ölçüm",
            min_value=1,
            max_value=100,
            value=3,
            step=1,
            key="prebreakout_calibration_minimum_sample",
        )
        summary = kalibrasyon_ozetini_hesapla(
            stage_rows,
            minimum_sample_size=int(minimum_sample_size),
        )

        metric_left, metric_middle, metric_right = st.columns(3)
        metric_left.metric("Ölçüm kapsamı", f"%{summary.measurement_coverage_pct:.2f}")
        metric_middle.metric("Ölçülen aday", summary.measured_count)
        metric_right.metric("Güvenilir aşama", summary.reliable_stage_count)

        if summary.best_stage is None:
            st.warning(summary.note)
        else:
            st.success(
                f"En yüksek gözlemsel başarı: {summary.best_stage} · "
                f"%{summary.best_stage_success_rate_pct:.2f}"
            )
            st.caption(summary.note)

        confidence_rows = asama_guven_araliklarini_hesapla(
            stage_rows,
            minimum_sample_size=int(minimum_sample_size),
        )
        conservative_leader = temkinli_lider_asamayi_sec(confidence_rows)
        if conservative_leader is not None:
            st.info(
                f"Temkinli lider: {conservative_leader.stage} · "
                f"%95 alt güven sınırı %{conservative_leader.confidence_low_pct:.2f}"
            )
        confidence_table = asama_guven_araliklarini_tabloya_cevir(confidence_rows)
        if not confidence_table.empty:
            st.subheader("Aşama başarı oranı güven aralıkları")
            st.dataframe(confidence_table, hide_index=True, width="stretch")
            st.download_button(
                "Güven aralıklarını CSV indir",
                data=confidence_table.to_csv(index=False).encode("utf-8-sig"),
                file_name="Hisse-Robotu-On-Yukselis-Guven-Araliklari.csv",
                mime="text/csv",
                width="stretch",
                key="prebreakout_confidence_interval_csv",
            )

        stability_summary = lider_kararlilik_ozetini_hesapla(
            stage_rows,
            minimum_sample_size=int(minimum_sample_size),
        )
        sensitivity_rows = lider_duyarlilik_senaryolarini_hesapla(
            stage_rows,
            minimum_sample_size=int(minimum_sample_size),
        )
        st.subheader("Temkinli lider kararlılığı")
        if stability_summary.baseline_leader is None:
            st.warning(stability_summary.note)
        else:
            stability_left, stability_right = st.columns(2)
            stability_left.metric(
                "Lider korunma oranı",
                f"%{stability_summary.retention_rate_pct:.2f}",
            )
            stability_right.metric(
                "Kararlılık",
                "Kararlı" if stability_summary.stable else "Kırılgan",
            )
            if stability_summary.stable:
                st.success(stability_summary.note)
            else:
                st.warning(stability_summary.note)

        sensitivity_table = lider_duyarlilik_senaryolarini_tabloya_cevir(
            sensitivity_rows
        )
        if not sensitivity_table.empty:
            st.dataframe(sensitivity_table, hide_index=True, width="stretch")
            st.download_button(
                "Lider duyarlılık senaryolarını CSV indir",
                data=sensitivity_table.to_csv(index=False).encode("utf-8-sig"),
                file_name="Hisse-Robotu-On-Yukselis-Lider-Duyarliligi.csv",
                mime="text/csv",
                width="stretch",
                key="prebreakout_leader_sensitivity_csv",
            )

        show_only_reliable = st.checkbox(
            "Yalnızca yeterli örneklemli aşamaları göster",
            value=False,
            key="prebreakout_calibration_reliable_only",
        )
        visible_stage_rows = (
            guvenilir_asama_satirlarini_sec(
                stage_rows,
                minimum_sample_size=int(minimum_sample_size),
            )
            if show_only_reliable
            else stage_rows
        )
        stage_table = asama_kalibrasyonunu_tabloya_cevir(visible_stage_rows)
        if not stage_table.empty:
            st.markdown("**Aşama bazında sonuçlar**")
            st.dataframe(stage_table, hide_index=True, width="stretch")
            st.download_button(
                "Aşama kalibrasyonunu CSV indir",
                data=stage_table.to_csv(index=False).encode("utf-8-sig"),
                file_name="Hisse-Robotu-On-Yukselis-Asama-Kalibrasyonu.csv",
                mime="text/csv",
                width="stretch",
                key="prebreakout_stage_calibration_csv",
            )
        elif show_only_reliable:
            st.info("Seçilen minimum örneklem koşulunu sağlayan aşama bulunamadı.")

        momentum_rows = momentum_kalibrasyonunu_hesapla(replay_results)
        momentum_table = momentum_kalibrasyonunu_tabloya_cevir(momentum_rows)
        if not momentum_table.empty:
            st.markdown("**Momentum, MACD ve RSI kırılımı**")
            st.dataframe(momentum_table, hide_index=True, width="stretch")
            st.download_button(
                "Momentum kalibrasyonunu CSV indir",
                data=momentum_table.to_csv(index=False).encode("utf-8-sig"),
                file_name="Hisse-Robotu-On-Yukselis-Momentum-Kalibrasyonu.csv",
                mime="text/csv",
                width="stretch",
                key="prebreakout_momentum_calibration_csv",
            )

        threshold_recommendations = kalibrasyon_esik_onerilerini_hesapla(
            stage_rows,
            momentum_rows,
            minimum_sample_size=int(minimum_sample_size),
        )
        threshold_table = kalibrasyon_esik_onerilerini_tabloya_cevir(
            threshold_recommendations
        )
        st.subheader("Kalibrasyona dayalı eşik önerileri")
        st.caption(
            "Bu öneriler üretim motoruna otomatik uygulanmaz. "
            "Sprint-91 karşılaştırmalı tarihsel doğrulaması için aday üretir."
        )
        if not threshold_table.empty:
            st.dataframe(threshold_table, hide_index=True, width="stretch")
            st.download_button(
                "Eşik önerilerini CSV indir",
                data=threshold_table.to_csv(index=False).encode("utf-8-sig"),
                file_name="Hisse-Robotu-On-Yukselis-Esik-Onerileri.csv",
                mime="text/csv",
                width="stretch",
                key="prebreakout_threshold_recommendations_csv",
            )

        threshold_validations = esik_onerilerini_tarihsel_dogrula(
            threshold_recommendations,
            momentum_rows,
            current_minimum_momentum_score=10,
        )
        validation_table = esik_dogrulamalarini_tabloya_cevir(
            threshold_validations
        )
        st.subheader("Eşik önerilerinin tarihsel karşılaştırması")
        st.caption(
            "Mevcut ve önerilen momentum eşikleri aynı tarihsel kalibrasyon "
            "örnekleminde karşılaştırılır; sonuçlar üretim motoruna otomatik uygulanmaz."
        )
        if validation_table.empty:
            st.info("Karşılaştırmalı doğrulamaya uygun eşik önerisi bulunamadı.")
        else:
            st.dataframe(validation_table, hide_index=True, width="stretch")
            st.download_button(
                "Eşik doğrulamasını CSV indir",
                data=validation_table.to_csv(index=False).encode("utf-8-sig"),
                file_name="Hisse-Robotu-On-Yukselis-Esik-Dogrulamasi.csv",
                mime="text/csv",
                width="stretch",
                key="prebreakout_threshold_validation_csv",
            )

        release_readiness = on_yukselis_surum_hazirligini_degerlendir(
            threshold_validations,
            mevcut_esik_politikasi(),
            leakage_guard_confirmed=True,
        )
        st.subheader("Ön Yükseliş Motoru sürüm hazırlığı")
        if release_readiness.ready:
            st.success(f"Kullanıma hazır · {release_readiness.message}")
        else:
            st.error(f"Kullanıma hazır değil · {release_readiness.message}")
        st.dataframe(
            surum_hazirligini_tabloya_cevir(release_readiness),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Geri alma: kontrollü eşik politikası kapatıldığında E2–E4 için "
            "varsayılan 10/20 momentum kapısı anında geri yüklenir."
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



def _render_daily_operations_hub(signals) -> None:
    st.subheader("Günlük Operasyon Merkezi")
    st.caption(
        "Canlı adaylar, aday yaşam döngüsü, gerçek sonuçlar, deneme portföyü ve "
        "sistem sağlığı günlük kullanım için tek bakışta özetlenir."
    )

    today = date.today().isoformat()
    todays_signals = [signal for signal in signals if signal.signal_date == today]
    e2_count = sum(1 for signal in signals if signal.stage == "E2")
    e3_count = sum(1 for signal in signals if signal.stage == "E3")
    e4_count = sum(1 for signal in signals if signal.stage == "E4")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam canlı aday", len(signals))
    col2.metric("Bugünkü yeni aday", len(todays_signals))
    col3.metric("E3–E4 güçlü hazırlık", e3_count + e4_count)
    col4.metric("E2 izleme", e2_count)

    operation_state = gunluk_operasyon_durumunu_yukle()
    st.markdown("Tek tuş günlük operasyon")
    if operation_state is None:
        st.info("Bugün için günlük operasyon kaydı henüz yok.")
    elif operation_state.status is DailyOperationStatus.COMPLETED:
        st.success("Günlük operasyon tamamlandı")
    elif operation_state.status is DailyOperationStatus.SKIPPED:
        st.info("Günlük operasyon zaten tamamlanmıştı")
    elif operation_state.status is DailyOperationStatus.BLOCKED:
        st.error("Günlük operasyon sağlık kilidinde")
    else:
        st.warning("Günlük operasyon güvenli yeniden denemeye hazır")
    if operation_state is not None:
        st.caption(
            f"Durum: {operation_state.status.value} · Deneme: {operation_state.attempt_count} · "
            f"Son adım: {operation_state.completed_steps[-1] if operation_state.completed_steps else 'Henüz yok'}"
        )

    st.markdown("Günlük işlem sırası")
    st.write(
        "1. Tarama ve yeni E2–E4 kayıtları → 2. Yaşam döngüsü → "
        "3. 5/10/20 günlük gerçek sonuçlar → 4. Deneme portföyü → "
        "5. Sistem sağlığı"
    )
    st.caption(
        "Bu panel karar özeti sağlar; ayrıntılı Canlı adaylar, Yaşam döngüsü, "
        "Gerçek sonuçlar, Deneme portföyü ve Sistem sağlığı bölümleri aşağıda korunur."
    )
    _render_operation_archive_history()

LEGACY_MANAGER_SUMMARY_LABEL = "Yönetici özeti"



def _render_operation_archive_history() -> None:
    st.subheader("Günlük Operasyon Arşivi")
    records = gunluk_operasyon_arsivini_yukle()
    if not records:
        st.info("Arşivlenmiş günlük operasyon sonucu henüz yok.")
        return

    current = records[-1]
    previous = records[-2] if len(records) > 1 else None
    st.markdown("Günlük Yönetici Özeti")
    st.write(yonetici_ozeti_olustur(current, previous))

    executive = gunluk_yonetici_ozetini_hesapla(records)
    if executive is not None:
        if executive.level is OperationTrendAlarmLevel.CRITICAL:
            st.error(executive.headline)
        elif executive.level is OperationTrendAlarmLevel.WARNING:
            st.warning(executive.headline)
        else:
            st.success(executive.headline)
        st.caption(executive.detail)
        if executive.alarms:
            st.markdown("Trend değişim alarmları")
            st.dataframe(
                pd.DataFrame(operasyon_alarmlarini_tabloya_cevir(executive.alarms)),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("Anlamlı günlük trend değişim alarmı yok.")

    st.markdown("Alarm geçmişi ve karar günlüğü")
    alarm_history = alarm_gecmisini_yukle()
    decision_history = karar_gunlugunu_yukle()
    left, right = st.columns(2)
    with left:
        st.markdown("Alarm geçmişi")
        if alarm_history:
            st.dataframe(
                pd.DataFrame(alarm_gecmisini_tabloya_cevir(alarm_history)),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("Kayıtlı alarm geçmişi yok.")
    with right:
        st.markdown("Günlük karar günlüğü")
        if decision_history:
            st.dataframe(
                pd.DataFrame(karar_gunlugunu_tabloya_cevir(decision_history)),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("Kayıtlı günlük karar yok.")

    comparison = gunluk_operasyon_karsilastirmasi(current, previous)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Yeni aday değişimi", comparison.new_signal_delta if comparison.new_signal_delta is not None else "—")
    col2.metric("Toplam aday değişimi", comparison.total_signal_delta if comparison.total_signal_delta is not None else "—")
    col3.metric(
        "Portföy değişimi",
        f"{comparison.portfolio_return_delta_pct:+.2f} puan" if comparison.portfolio_return_delta_pct is not None else "—",
    )
    col4.metric("Sağlık değişti", "Evet" if comparison.health_changed else "Hayır")

    st.markdown("Geçmiş gün karşılaştırması")
    st.dataframe(
        pd.DataFrame(gunluk_operasyon_arsivini_tabloya_cevir(records)),
        hide_index=True,
        width="stretch",
    )


def _render_live_performance_comparison(records, *, sectors=None, market_regimes=None, threshold_modes=None) -> None:
    st.subheader("Canlı performans karşılaştırması")
    rows = performans_karsilastirmasini_hesapla(
        records,
        sectors=sectors,
        market_regimes=market_regimes,
        threshold_modes=threshold_modes,
    )
    table = performans_karsilastirmasini_tabloya_cevir(rows)
    if table.empty:
        st.info("Karşılaştırma için ölçülebilir canlı sonuç bulunamadı.")
        return
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button(
        "Performans karşılaştırmasını CSV indir",
        data=table.to_csv(index=False).encode("utf-8-sig"),
        file_name="Hisse-Robotu-Canli-Performans-Karsilastirmasi.csv",
        mime="text/csv",
        width="stretch",
        key="prebreakout_live_performance_comparison_csv",
    )


def _render_paper_portfolio(signals) -> None:
    st.subheader("Deneme Portföyü")
    st.caption(
        "Gerçek emir gönderilmez. Sanal giriş, stop, hedef, pozisyon büyüklüğü, "
        "işlem maliyeti ve kayma varsayımlarıyla sonuçlar izlenir."
    )
    config = PaperPortfolioConfig()
    trades = []
    for signal in signals:
        start_day = date.fromisoformat(signal.signal_date)
        price_data = _download_single_symbol(
            signal.symbol,
            start_date=start_day,
            end_date=date.today(),
        )
        observations = tuple(
            CandidatePriceObservation(
                observation_date=index.date(),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
            )
            for index, row in price_data.iterrows()
            if index.date() > start_day
        )
        trades.append(deneme_islemini_hesapla(signal, observations, config=config))

    summary = deneme_portfoyu_ozeti(trades, initial_capital=config.initial_capital)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Açık pozisyon", summary.open_trade_count)
    col2.metric("Kapanan pozisyon", summary.closed_trade_count)
    col3.metric("Net sonuç", f"{summary.total_net_pnl:,.2f} TL")
    col4.metric("Portföy getirisi", f"%{summary.portfolio_return_pct:.2f}")
    st.caption(
        f"Kazanma oranı: {summary.win_rate_pct if summary.win_rate_pct is not None else 0:.2f}% · "
        f"Maksimum düşüş: %{summary.maximum_drawdown_pct:.2f}"
    )
    table = deneme_portfoyunu_tabloya_cevir(trades)
    st.dataframe(table, hide_index=True, width="stretch")
    st.download_button(
        "Deneme portföyünü CSV indir",
        data=table.to_csv(index=False).encode("utf-8-sig"),
        file_name="Hisse-Robotu-Deneme-Portfoyu.csv",
        mime="text/csv",
        width="stretch",
        key="prebreakout_paper_portfolio_csv",
    )


def _render_operational_health(signals, lifecycle_records, performance_records) -> None:
    st.subheader("Operasyon ve Sistem Sağlığı")

    class _PortfolioSummary:
        total_trade_count = len(signals)

    class _DailyView:
        run_date = date.today().isoformat()
        total_signal_count = len(signals)
        missing_observation_symbols = tuple(
            record.symbol
            for record in performance_records
            if int(getattr(record, "available_session_count", 0) or 0) == 0
        )
        portfolio_summary = _PortfolioSummary()

    daily_view = _DailyView()
    daily_view.lifecycle_records = tuple(lifecycle_records)
    daily_view.performance_records = tuple(performance_records)
    daily_view.paper_trades = tuple(signals)
    report = operasyon_sagligini_degerlendir(
        daily_view,
        expected_run_date=date.today(),
    )
    if report.ready:
        if report.warning_count:
            st.warning(f"Sistem hazır · {report.warning_count} uyarı")
        else:
            st.success("Sistem hazır")
    else:
        st.error("Sistem hazır değil" + f" · {report.error_count} hata")
    st.dataframe(
        pd.DataFrame(operasyon_sagligini_tabloya_cevir(report)),
        hide_index=True,
        width="stretch",
    )


def _render_real_result_evaluation(signals, lifecycle_records, performance_records) -> None:
    st.subheader("Gerçek Sonuç Değerlendirmesi")
    config = PaperPortfolioConfig()
    trades = []
    threshold_modes = {}
    for signal in signals:
        threshold_modes[signal.signal_id] = "Kalibre" if signal.threshold_policy_enabled else "Varsayılan"
        start_day = date.fromisoformat(signal.signal_date)
        price_data = _download_single_symbol(signal.symbol, start_date=start_day, end_date=date.today())
        observations = tuple(
            CandidatePriceObservation(observation_date=index.date(), high=float(row["High"]), low=float(row["Low"]), close=float(row["Close"]))
            for index, row in price_data.iterrows() if index.date() > start_day
        )
        trades.append(deneme_islemini_hesapla(signal, observations, config=config))
    evaluation = gercek_sonuclari_degerlendir(
        performance_records, lifecycle_records, trades,
        threshold_modes=threshold_modes, initial_capital=config.initial_capital,
    )
    if evaluation.sufficient_sample:
        st.success(evaluation.note)
    else:
        st.warning(evaluation.note)
    left, middle, right = st.columns(3)
    left.metric("Ölçülen sonuç", evaluation.measured_count)
    middle.metric("Başarılı", evaluation.successful_count)
    right.metric("Net portföy getirisi", f"%{evaluation.portfolio_summary.portfolio_return_pct:.2f}")
    st.dataframe(gercek_sonuc_asama_tablosu(evaluation), hide_index=True, width="stretch")
    threshold_table = gercek_sonuc_esik_tablosu(evaluation)
    if not threshold_table.empty:
        st.markdown("Varsayılan / kalibre eşik karşılaştırması")
        st.dataframe(threshold_table, hide_index=True, width="stretch")
