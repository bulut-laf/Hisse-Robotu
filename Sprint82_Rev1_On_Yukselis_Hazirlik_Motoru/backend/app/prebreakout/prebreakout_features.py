from __future__ import annotations

import numpy as np
import pandas as pd

from backend.app.prebreakout.prebreakout_models import PreBreakoutFeatures


REQUIRED_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


class PreBreakoutDataError(ValueError):
    pass


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    result = 100.0 - (100.0 / (1.0 + rs))
    both_zero = (avg_gain == 0.0) & (avg_loss == 0.0)
    result = result.mask(both_zero, 50.0)
    result = result.mask((avg_loss == 0.0) & (avg_gain > 0.0), 100.0)
    return result


def _atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = data["Close"].shift(1)
    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - previous_close).abs(),
            (data["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def _safe_pct(numerator: float, denominator: float) -> float:
    if denominator == 0.0 or not np.isfinite(denominator):
        return 0.0
    return float((numerator / denominator) * 100.0)


def _average_or_zero(series: pd.Series) -> float:
    clean = series.dropna()
    return float(clean.mean()) if not clean.empty else 0.0


def ozellikleri_hesapla(
    data: pd.DataFrame,
    *,
    resistance_window: int = 20,
) -> PreBreakoutFeatures:
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise PreBreakoutDataError(
            "Eksik OHLCV sütunları: " + ", ".join(missing)
        )
    if len(data) < 60:
        raise PreBreakoutDataError(
            f"En az 60 tamamlanmış günlük bar gerekir. Mevcut: {len(data)}"
        )

    clean = data.loc[:, REQUIRED_COLUMNS].copy()
    clean = clean.apply(pd.to_numeric, errors="coerce").dropna()
    if len(clean) < 60:
        raise PreBreakoutDataError(
            "Temizleme sonrasında en az 60 geçerli günlük bar gerekir."
        )
    if (clean["Close"] <= 0).any() or (clean["Volume"] < 0).any():
        raise PreBreakoutDataError("Fiyat ve hacim değerleri geçersiz.")

    close = clean["Close"]
    volume = clean["Volume"]
    ema9 = _ema(close, 9)
    ema21 = _ema(close, 21)
    ema50 = _ema(close, 50)
    rsi14 = _rsi(close, 14)

    macd = _ema(close, 12) - _ema(close, 26)
    macd_signal = _ema(macd, 9)
    macd_hist = macd - macd_signal

    atr14 = _atr(clean, 14)
    atr_pct_series = (atr14 / close) * 100.0

    latest_close = float(close.iloc[-1])
    latest_atr = float(atr14.iloc[-1])
    latest_atr_pct = float(atr_pct_series.iloc[-1])
    previous_atr_mean = _average_or_zero(atr_pct_series.iloc[-20:-5])
    atr_contraction = (
        latest_atr_pct / previous_atr_mean
        if previous_atr_mean > 0
        else 1.0
    )

    daily_range_pct = ((clean["High"] - clean["Low"]) / close) * 100.0
    recent_range = _average_or_zero(daily_range_pct.iloc[-5:])
    previous_range = _average_or_zero(daily_range_pct.iloc[-20:-5])
    range_contraction = (
        recent_range / previous_range
        if previous_range > 0
        else 1.0
    )

    average_volume_3 = _average_or_zero(volume.iloc[-3:])
    average_volume_10_previous = _average_or_zero(volume.iloc[-13:-3])
    volume_ratio_3_10 = (
        average_volume_3 / average_volume_10_previous
        if average_volume_10_previous > 0
        else 0.0
    )

    returns = close.pct_change()
    up_volume = volume.where(returns > 0)
    down_volume = volume.where(returns < 0)
    volume20 = _average_or_zero(volume.iloc[-20:])
    up_volume_ratio = (
        _average_or_zero(up_volume.iloc[-10:]) / volume20
        if volume20 > 0
        else 0.0
    )
    down_volume_ratio = (
        _average_or_zero(down_volume.iloc[-10:]) / volume20
        if volume20 > 0
        else 0.0
    )

    prior_resistance = float(
        clean["High"].iloc[-(resistance_window + 1):-1].max()
    )
    resistance_distance = _safe_pct(
        prior_resistance - latest_close,
        latest_close,
    )

    recent_lows = clean["Low"].iloc[-20:]
    first_half_low = float(recent_lows.iloc[:10].min())
    second_half_low = float(recent_lows.iloc[10:].min())
    rising_low = second_half_low > first_half_low

    stop = latest_close - (1.5 * latest_atr)
    target = prior_resistance + latest_atr
    risk = max(latest_close - stop, 0.0)
    reward = max(target - latest_close, 0.0)
    risk_reward = reward / risk if risk > 0 else 0.0

    return PreBreakoutFeatures(
        close=latest_close,
        ema9=float(ema9.iloc[-1]),
        ema21=float(ema21.iloc[-1]),
        ema50=float(ema50.iloc[-1]),
        rsi14=float(rsi14.iloc[-1]),
        rsi_egimi=float(rsi14.iloc[-1] - rsi14.iloc[-4]),
        macd=float(macd.iloc[-1]),
        macd_sinyal=float(macd_signal.iloc[-1]),
        macd_histogram=float(macd_hist.iloc[-1]),
        macd_histogram_egimi=float(macd_hist.iloc[-1] - macd_hist.iloc[-4]),
        atr14=latest_atr,
        atr_pct=latest_atr_pct,
        atr_daralma_orani=float(atr_contraction),
        bes_gun_aralik_daralma_orani=float(range_contraction),
        ema9_ema21_mesafe_pct=_safe_pct(
            float(ema9.iloc[-1] - ema21.iloc[-1]),
            float(ema21.iloc[-1]),
        ),
        ema21_uzaklik_pct=_safe_pct(
            latest_close - float(ema21.iloc[-1]),
            float(ema21.iloc[-1]),
        ),
        ema21_egimi_pct=_safe_pct(
            float(ema21.iloc[-1] - ema21.iloc[-6]),
            float(ema21.iloc[-6]),
        ),
        hacim_orani_3_10=float(volume_ratio_3_10),
        yukselis_hacim_orani=float(up_volume_ratio),
        dusus_hacim_orani=float(down_volume_ratio),
        direnc=prior_resistance,
        direnc_uzaklik_pct=float(resistance_distance),
        son_gun_getirisi_pct=float(returns.iloc[-1] * 100.0),
        uc_gun_getirisi_pct=_safe_pct(
            latest_close - float(close.iloc[-4]),
            float(close.iloc[-4]),
        ),
        bes_gun_getirisi_pct=_safe_pct(
            latest_close - float(close.iloc[-6]),
            float(close.iloc[-6]),
        ),
        yukselen_dip=rising_low,
        risk_odul=float(risk_reward),
    )
