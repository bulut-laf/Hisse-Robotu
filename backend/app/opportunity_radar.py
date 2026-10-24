from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from backend.app.data.batch_market_data import BatchMarketDataFailure, toplu_fiyat_verisi_getir
from backend.app.data.market_data import fiyat_verisi_getir
from backend.app.prebreakout.prebreakout_universe import on_yukselis_evrenini_yukle


PROFILE_DIR = Path(__file__).resolve().parents[1] / "data" / "opportunity_radar"
QUANTILE_FILE = PROFILE_DIR / "03_w2_w3_quantile_sinirlari_rev3.csv"
PASSED_PROFILE_FILE = PROFILE_DIR / "06_w2_w3_gecen_profiller_rev3.csv"
MONTHLY_QUANTILE_FILE = PROFILE_DIR / "03_aylik_quantile_sinirlari_rev2.csv"
MONTHLY_PASSED_PROFILE_FILE = PROFILE_DIR / "06_aylik_gecen_profiller_rev2.csv"


@dataclass(frozen=True)
class OpportunityRadarResult:
    universe_name: str
    universe_source: str
    universe_date: str
    universe_count: int
    data_success_count: int
    data_failures: tuple[BatchMarketDataFailure, ...]
    weekly: pd.DataFrame
    monthly_strong: pd.DataFrame
    monthly_early: pd.DataFrame


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = [str(c[0]) for c in x.columns]
    cmap = {str(c).strip().lower(): c for c in x.columns}
    needed = {"open": "Open", "high": "High", "low": "Low", "close": "Close"}
    missing = [src for src in needed if src not in cmap]
    if missing:
        raise ValueError("Eksik OHLC kolonlari: " + ", ".join(missing))
    out = pd.DataFrame(index=pd.to_datetime(x.index))
    for src, dest in needed.items():
        out[dest] = pd.to_numeric(x[cmap[src]], errors="coerce")
    vol = cmap.get("volume")
    out["Volume"] = pd.to_numeric(x[vol], errors="coerce") if vol else np.nan
    out = out.dropna(subset=["Open", "High", "Low", "Close"]).sort_index()
    return out[(out["High"] >= out["Low"]) & (out["Close"] >= out["Low"]) & (out["Close"] <= out["High"])]


def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    delta = s.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    au = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    ad = down.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = au / ad.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def _weekly(daily: pd.DataFrame) -> pd.DataFrame:
    d = _normalize_ohlcv(daily)
    return pd.DataFrame(
        {
            "Open": d["Open"].resample("W-FRI").first(),
            "High": d["High"].resample("W-FRI").max(),
            "Low": d["Low"].resample("W-FRI").min(),
            "Close": d["Close"].resample("W-FRI").last(),
            "Volume": d["Volume"].resample("W-FRI").sum(min_count=1),
        }
    ).dropna(subset=["Open", "High", "Low", "Close"])


def _weekly_enrich(w: pd.DataFrame) -> pd.DataFrame:
    # Research V1 Rev1 W1-W4 contract is intentionally preserved.
    z = w.copy()
    z["EMA20"] = z["Close"].ewm(span=20, adjust=False).mean()
    z["EMA50"] = z["Close"].ewm(span=50, adjust=False).mean()
    z["EMA20Slope4"] = z["EMA20"] / z["EMA20"].shift(4) - 1
    z["RSI14"] = _rsi(z["Close"])
    z["RSIDelta3"] = z["RSI14"] - z["RSI14"].shift(3)

    prev_close = z["Close"].shift(1)
    tr = pd.concat(
        [
            z["High"] - z["Low"],
            (z["High"] - prev_close).abs(),
            (z["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    z["ATR14"] = tr.rolling(14).mean()
    z["ATRPct"] = 100 * z["ATR14"] / z["Close"]
    z["ATRContract"] = z["ATRPct"] < z["ATRPct"].rolling(8).mean()
    z["VolMA8"] = z["Volume"].rolling(8).mean()
    z["VolRatio"] = z["Volume"] / z["VolMA8"].replace(0, np.nan)
    z["Res26"] = z["High"].shift(1).rolling(26, min_periods=13).max()
    z["DistResPct"] = 100 * (z["Res26"] - z["Close"]) / z["Close"]
    z["Breakout26"] = z["Close"] > z["Res26"]

    r6 = (z["High"].rolling(6).max() - z["Low"].rolling(6).min()) / z["Close"]
    z["Compression"] = r6 < r6.shift(6)
    z["AboveEMA20"] = z["Close"] >= z["EMA20"]
    z["AboveEMA50"] = z["Close"] >= z["EMA50"]

    trend = z["AboveEMA20"].astype(int) * 8 + z["AboveEMA50"].astype(int) * 5 + (z["EMA20Slope4"] > 0).astype(int) * 7
    momentum = (z["RSI14"] >= 50).astype(int) * 8 + (z["RSI14"] <= 72).astype(int) * 4 + (z["RSIDelta3"] > 0).astype(int) * 8
    compression = z["Compression"].astype(int) * 12 + z["ATRContract"].astype(int) * 8
    proximity = np.select(
        [
            z["Breakout26"],
            z["DistResPct"].between(0, 5),
            z["DistResPct"].between(5, 12),
            z["DistResPct"].between(12, 20),
        ],
        [15, 15, 10, 5],
        default=0,
    )
    volume = np.select(
        [z["VolRatio"] >= 1.5, z["VolRatio"] >= 1.1, z["VolRatio"] >= 0.8],
        [15, 12, 7],
        default=2,
    )
    z["WeeklyScore"] = ((trend + momentum + compression + proximity + volume) / 90 * 100).round(2)

    stage = pd.Series("NONE", index=z.index, dtype="object")
    w4 = z["Breakout26"] & z["AboveEMA20"] & (z["EMA20Slope4"] > 0) & (z["RSI14"] >= 50) & (z["VolRatio"].fillna(0) >= 1.0)
    w3 = (
        (~w4)
        & z["DistResPct"].between(0, 5)
        & z["AboveEMA20"]
        & (z["EMA20Slope4"] > 0)
        & z["RSI14"].between(50, 72)
        & (z["RSIDelta3"] >= 0)
        & (z["Compression"] | z["ATRContract"])
        & (z["VolRatio"].fillna(1) >= 0.8)
    )
    w2 = (
        (~w4)
        & (~w3)
        & z["DistResPct"].between(5, 12)
        & (z["Close"] >= z["EMA20"] * 0.97)
        & (z["EMA20Slope4"] >= -0.01)
        & (z["RSI14"] >= 45)
        & (z["RSIDelta3"] >= 0)
    )
    stage[w2] = "W2"
    stage[w3] = "W3"
    stage[w4] = "W4"
    z["Stage"] = stage
    return z


def _load_validated_profiles() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not QUANTILE_FILE.exists() or not PASSED_PROFILE_FILE.exists():
        raise RuntimeError(
            "Validated profil dosyalari kurulu degil. "
            "Firsat Radari kurucusunu Rev3 research ciktilari mevcutken tekrar calistirin."
        )
    edges = pd.read_csv(QUANTILE_FILE)
    profiles = pd.read_csv(PASSED_PROFILE_FILE)
    required_edges = {"factor", "bin", "lower_exclusive_or_equal", "upper_inclusive"}
    required_profiles = {
        "stage", "factor_1", "bin_1", "factor_2", "bin_2",
        "valid_n", "valid_median_excess_4w_pct", "valid_median_excess_8w_pct",
        "validation_quality_score",
    }
    if not required_edges.issubset(edges.columns):
        raise RuntimeError("Validated quantile dosyasi beklenen kolonlari tasimiyor.")
    if not required_profiles.issubset(profiles.columns):
        raise RuntimeError("Validated profil dosyasi beklenen kolonlari tasimiyor.")
    return edges, profiles



def _load_monthly_validated_profiles() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not MONTHLY_QUANTILE_FILE.exists() or not MONTHLY_PASSED_PROFILE_FILE.exists():
        raise RuntimeError("Aylik validated profil dosyalari kurulu degil.")
    edges = pd.read_csv(MONTHLY_QUANTILE_FILE)
    profiles = pd.read_csv(MONTHLY_PASSED_PROFILE_FILE)
    required_edges = {"monthly_class", "factor", "bin", "lower", "upper"}
    required_profiles = {
        "monthly_class", "factor_1", "bin_1", "factor_2", "bin_2",
        "valid_n", "valid_median_excess_3m_pct", "valid_median_excess_6m_pct",
        "validation_quality_score",
    }
    if not required_edges.issubset(edges.columns):
        raise RuntimeError("Aylik quantile dosyasi beklenen kolonlari tasimiyor.")
    if not required_profiles.issubset(profiles.columns):
        raise RuntimeError("Aylik profil dosyasi beklenen kolonlari tasimiyor.")
    return edges, profiles


def _monthly_validation_months(daily: pd.DataFrame) -> pd.DataFrame:
    d = _normalize_ohlcv(daily).rename(
        columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"}
    )
    p = d.index.to_period("M")
    m = d.groupby(p).agg(
        open=("open","first"), high=("high","max"), low=("low","min"),
        close=("close","last"), volume=("volume","sum"),
    )
    m.index = m.index.to_timestamp(how="end").normalize()
    return m


def _monthly_validation_features(daily: pd.DataFrame) -> pd.DataFrame:
    x = _monthly_validation_months(daily)
    x["ema6"] = x["close"].ewm(span=6, adjust=False, min_periods=6).mean()
    x["ema12"] = x["close"].ewm(span=12, adjust=False, min_periods=12).mean()
    x["ema24"] = x["close"].ewm(span=24, adjust=False, min_periods=24).mean()
    x["rsi14"] = _rsi(x["close"], 14)
    prev = x["close"].shift(1)
    tr = pd.concat([
        x["high"] - x["low"],
        (x["high"] - prev).abs(),
        (x["low"] - prev).abs(),
    ], axis=1).max(axis=1)
    x["atr14"] = tr.rolling(14, min_periods=14).mean()
    x["atr_pct"] = 100 * x["atr14"] / x["close"]
    x["vol_ratio"] = x["volume"] / x["volume"].rolling(6, min_periods=6).mean().replace(0, np.nan)
    x["ret_3m"] = 100 * (x["close"] / x["close"].shift(3) - 1)
    x["ret_6m"] = 100 * (x["close"] / x["close"].shift(6) - 1)
    x["ema6_slope"] = 100 * (x["ema6"] / x["ema6"].shift(3) - 1)

    strong = (
        (x["close"] > x["ema6"])
        & (x["ema6"] > x["ema12"])
        & (x["ema12"] > x["ema24"])
        & (x["ema6_slope"] > 0)
        & (x["ret_3m"] > 0)
    )
    early = (
        (x["close"] > x["ema6"])
        & ((x["ema6"] >= x["ema12"]) | ((x["ema6"] < x["ema12"]) & (x["ema6_slope"] > 0)))
        & (x["ret_3m"] > -10)
        & (x["rsi14"].between(45, 70))
        & (~strong)
    )
    x["research_class"] = np.where(strong, "GUCLU_TREND", np.where(early, "ERKEN_TREND", "DIGER"))
    return x


def _monthly_profile_matches(row: pd.Series, edges: pd.DataFrame, profiles: pd.DataFrame) -> list[dict[str, object]]:
    cls = str(row.get("research_class", ""))
    if cls not in {"GUCLU_TREND", "ERKEN_TREND"}:
        return []
    matches = []
    for _, p in profiles[profiles["monthly_class"] == cls].iterrows():
        ok = True
        for factor_col, bin_col in (("factor_1","bin_1"),("factor_2","bin_2")):
            factor = str(p[factor_col])
            bin_name = str(p[bin_col])
            erow = edges[
                (edges["monthly_class"] == cls)
                & (edges["factor"] == factor)
                & (edges["bin"] == bin_name)
            ]
            if erow.empty or factor not in row.index or pd.isna(row[factor]):
                ok = False
                break
            lo = float(erow.iloc[0]["lower"])
            hi = float(erow.iloc[0]["upper"])
            value = float(row[factor])
            if not ((np.isneginf(lo) or value > lo) and (np.isposinf(hi) or value <= hi)):
                ok = False
                break
        if ok:
            matches.append({
                "quality": float(p["validation_quality_score"]),
                "profile": f'{cls}: {p["factor_1"]}={p["bin_1"]} + {p["factor_2"]}={p["bin_2"]}',
                "excess3": float(p["valid_median_excess_3m_pct"]),
                "excess6": float(p["valid_median_excess_6m_pct"]),
            })
    return matches


def _monthly_profile_snapshots(daily: pd.DataFrame, edges: pd.DataFrame, profiles: pd.DataFrame):
    z = _monthly_validation_features(daily)
    if z.empty:
        return {"snapshot":"CURRENT_PARTIAL","matches":[]}, {"snapshot":"LAST_CLOSED","matches":[]}
    d = _normalize_ohlcv(daily)
    last_daily = pd.Timestamp(d.index.max()).normalize()
    current_end = last_daily.to_period("M").to_timestamp(how="end").normalize()
    is_partial = z.index[-1] == current_end and last_daily < current_end

    current = {
        "snapshot": "CURRENT_PARTIAL" if is_partial else "CURRENT_CLOSED",
        "matches": _monthly_profile_matches(z.iloc[-1], edges, profiles),
    }
    closed_row = z.iloc[-2] if is_partial and len(z) >= 2 else z.iloc[-1]
    closed = {
        "snapshot": "LAST_CLOSED" if is_partial else "CURRENT_CLOSED",
        "matches": _monthly_profile_matches(closed_row, edges, profiles),
    }
    return current, closed


def _monthly_profile_status(current: dict[str, object], closed: dict[str, object]) -> dict[str, object]:
    current_matches = list(current.get("matches", []))
    closed_matches = list(closed.get("matches", []))
    if current.get("snapshot") == "CURRENT_PARTIAL" and current_matches:
        chosen = current_matches
        status = "Ay İçi Geçici Match"
    elif closed_matches:
        chosen = closed_matches
        status = "Validated Profile Match"
    else:
        chosen = []
        status = "Henüz Validate Değil"

    if not chosen:
        return {
            "Durum": status, "Profile Match Count": 0, "Validated Quality": 0.0,
            "Geçmiş 3A Excess %": np.nan, "Geçmiş 6A Excess %": np.nan,
            "Validation Profili": "",
        }
    return {
        "Durum": status,
        "Profile Match Count": len(chosen),
        "Validated Quality": round(sum(float(x["quality"]) for x in chosen), 2),
        "Geçmiş 3A Excess %": round(max(float(x["excess3"]) for x in chosen), 2),
        "Geçmiş 6A Excess %": round(max(float(x["excess6"]) for x in chosen), 2),
        "Validation Profili": " | ".join(str(x["profile"]) for x in chosen),
    }


def _apply_monthly_validation(frame, validation_data, edges, profiles):
    if frame.empty:
        return frame
    out = frame.copy()
    payloads = []
    for _, row in out.iterrows():
        symbol = str(row["Hisse"])
        daily = validation_data.get(symbol) or validation_data.get(symbol + ".IS")
        if daily is None:
            payloads.append(_monthly_profile_status(
                {"snapshot":"CURRENT_PARTIAL","matches":[]},
                {"snapshot":"LAST_CLOSED","matches":[]},
            ))
            continue
        try:
            current, closed = _monthly_profile_snapshots(daily, edges, profiles)
            payloads.append(_monthly_profile_status(current, closed))
        except Exception:
            payloads.append(_monthly_profile_status(
                {"snapshot":"CURRENT_PARTIAL","matches":[]},
                {"snapshot":"LAST_CLOSED","matches":[]},
            ))
    p = pd.DataFrame(payloads, index=out.index)
    for col in p.columns:
        out[col] = p[col]
    return out


def _bin_ranges(edges: pd.DataFrame) -> dict[tuple[str, str], tuple[float, float]]:
    result: dict[tuple[str, str], tuple[float, float]] = {}
    for _, row in edges.iterrows():
        lo = -np.inf if pd.isna(row["lower_exclusive_or_equal"]) else float(row["lower_exclusive_or_equal"])
        hi = np.inf if pd.isna(row["upper_inclusive"]) else float(row["upper_inclusive"])
        result[(str(row["factor"]), str(row["bin"]))] = (lo, hi)
    return result


def _in_bin(value: object, factor: str, bin_name: str, ranges: dict[tuple[str, str], tuple[float, float]]) -> bool:
    if pd.isna(value):
        return False
    bounds = ranges.get((factor, bin_name))
    if bounds is None:
        return False
    lo, hi = bounds
    number = float(value)
    return (np.isneginf(lo) or number > lo) and number <= hi


def _weekly_row(symbol: str, daily: pd.DataFrame, edges: pd.DataFrame, profiles: pd.DataFrame) -> dict[str, object] | None:
    w = _weekly_enrich(_weekly(daily))
    if len(w) < 26:
        return None
    r = w.iloc[-1]
    stage = str(r["Stage"])
    if stage not in {"W2", "W3"}:
        return None

    base = {
        "Hisse": symbol.removesuffix(".IS"),
        "W2 / W3": stage,
        "Weekly Score": float(r["WeeklyScore"]),
        "Direnç Uzaklığı %": float(r["DistResPct"]),
        "RSI": float(r["RSI14"]),
        "Hacim Oranı": float(r["VolRatio"]),
        "ATR %": float(r["ATRPct"]),
        "Kapanış": float(r["Close"]),
        "Hafta": w.index[-1].date().isoformat(),
    }
    factor_values = {
        "weekly_score": base["Weekly Score"],
        "dist_res_pct": base["Direnç Uzaklığı %"],
        "rsi14": base["RSI"],
        "vol_ratio": base["Hacim Oranı"],
        "atr_pct": base["ATR %"],
    }
    ranges = _bin_ranges(edges)
    matched: list[pd.Series] = []
    for _, p in profiles.iterrows():
        if stage != str(p["stage"]):
            continue
        f1, b1 = str(p["factor_1"]), str(p["bin_1"])
        f2, b2 = str(p["factor_2"]), str(p["bin_2"])
        if (
            f1 in factor_values
            and f2 in factor_values
            and _in_bin(factor_values[f1], f1, b1, ranges)
            and _in_bin(factor_values[f2], f2, b2, ranges)
        ):
            matched.append(p)

    if matched:
        qualities = [float(p["validation_quality_score"]) for p in matched]
        base.update(
            {
                "Validated Profile Count": len(matched),
                "Validated Quality": round(sum(qualities), 2),
                "Validated Quality Max": round(max(qualities), 2),
                "Geçmiş 4H Excess %": round(max(float(p["valid_median_excess_4w_pct"]) for p in matched), 2),
                "Geçmiş 8H Excess %": round(max(float(p["valid_median_excess_8w_pct"]) for p in matched), 2),
                "Durum": "Validated",
                "Neden seçildi?": " | ".join(
                    f'{p["stage"]}: {p["factor_1"]}={p["bin_1"]} + {p["factor_2"]}={p["bin_2"]}'
                    for p in matched
                ),
            }
        )
    else:
        base.update(
            {
                "Validated Profile Count": 0,
                "Validated Quality": 0.0,
                "Validated Quality Max": 0.0,
                "Geçmiş 4H Excess %": np.nan,
                "Geçmiş 8H Excess %": np.nan,
                "Durum": "Henüz Validate Değil",
                "Neden seçildi?": f"{stage} hazırlık koşulları var; muhafazakâr validated profile eşleşmedi.",
            }
        )
    return base


def _monthly(daily: pd.DataFrame) -> pd.DataFrame:
    d = _normalize_ohlcv(daily)
    period = d.index.to_period("M")
    m = d.groupby(period).agg(
        Open=("Open", "first"),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
        Volume=("Volume", "sum"),
    )
    m.index = m.index.to_timestamp(how="end").normalize()
    return m.dropna(subset=["Open", "High", "Low", "Close"])


def _monthly_metrics(daily: pd.DataFrame, benchmark: pd.DataFrame | None) -> dict[str, object] | None:
    m = _monthly(daily)
    if len(m) < 12:
        return None
    close, high, low, volume = m["Close"], m["High"], m["Low"], m["Volume"]
    ema6 = close.ewm(span=6, adjust=False).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    rsi = _rsi(close, 6)
    prev_close = close.shift(1)
    tr = pd.concat([high-low, (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    atr = tr.rolling(6).mean()
    res12 = high.shift(1).rolling(12, min_periods=6).max()
    vol_ma6 = volume.rolling(6).mean()

    last = len(m) - 1
    ret3 = float(close.iloc[last] / close.iloc[max(0, last-3)] - 1)
    ret6 = float(close.iloc[last] / close.iloc[max(0, last-6)] - 1)
    bench3 = bench6 = np.nan
    benchmark_available = False
    if benchmark is not None:
        bm = _monthly(benchmark)
        if len(bm) >= 7:
            bc = bm["Close"]
            bench3 = float(bc.iloc[-1] / bc.iloc[-4] - 1)
            bench6 = float(bc.iloc[-1] / bc.iloc[-7] - 1)
            benchmark_available = True

    dist = float(100 * (res12.iloc[-1] - close.iloc[-1]) / close.iloc[-1]) if pd.notna(res12.iloc[-1]) else np.nan
    vol_ratio = float(volume.iloc[-1] / vol_ma6.iloc[-1]) if pd.notna(vol_ma6.iloc[-1]) and vol_ma6.iloc[-1] > 0 else np.nan
    atr_pct = float(100 * atr.iloc[-1] / close.iloc[-1]) if pd.notna(atr.iloc[-1]) else np.nan
    ema6_slope3 = float(ema6.iloc[-1] / ema6.iloc[-4] - 1) if len(ema6) >= 4 and ema6.iloc[-4] else 0.0
    rsi_delta2 = float(rsi.iloc[-1] - rsi.iloc[-3]) if len(rsi) >= 3 else 0.0
    higher_high = bool(high.tail(3).max() >= high.iloc[-6:-3].max()) if len(high) >= 6 else False
    higher_low = bool(low.tail(3).min() > low.iloc[-6:-3].min()) if len(low) >= 6 else False

    return {
        "close": float(close.iloc[-1]),
        "ema6": float(ema6.iloc[-1]),
        "ema12": float(ema12.iloc[-1]),
        "ema6_slope3": ema6_slope3,
        "rsi": float(rsi.iloc[-1]),
        "rsi_delta2": rsi_delta2,
        "dist": dist,
        "vol_ratio": vol_ratio,
        "atr_pct": atr_pct,
        "ret3": ret3,
        "ret6": ret6,
        "excess3": ret3 - bench3 if benchmark_available else np.nan,
        "excess6": ret6 - bench6 if benchmark_available else np.nan,
        "benchmark_available": benchmark_available,
        "higher_high": higher_high,
        "higher_low": higher_low,
        "month": m.index[-1].date().isoformat(),
    }


def _monthly_rows(symbol: str, daily: pd.DataFrame, benchmark: pd.DataFrame | None) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    x = _monthly_metrics(daily, benchmark)
    if x is None:
        return None, None

    strong_score = 0
    strong_reasons: list[str] = []
    if x["close"] > x["ema6"] > x["ema12"]:
        strong_score += 30
        strong_reasons.append("Aylık fiyat EMA6 ve EMA12 üzerinde; ortalamalar yukarı sıralı.")
    if x["ema6_slope3"] > 0:
        strong_score += 15
        strong_reasons.append("Aylık kısa trend eğimi pozitif.")
    if x["benchmark_available"] and x["excess6"] > 0:
        strong_score += 20
        strong_reasons.append("6 aylık göreli performans XU100 üzerinde.")
    if 52 <= x["rsi"] <= 75:
        strong_score += 10
        strong_reasons.append("Aylık momentum güçlü fakat aşırı değil.")
    if x["higher_high"]:
        strong_score += 10
        strong_reasons.append("Aylık higher-high yapısı korunuyor.")
    if x["higher_low"]:
        strong_score += 10
        strong_reasons.append("Aylık higher-low yapısı korunuyor.")
    if pd.notna(x["vol_ratio"]) and x["vol_ratio"] >= 1.0:
        strong_score += 5
        strong_reasons.append("Aylık hacim 6 aylık ortalamanın üzerinde.")

    strong = None
    if strong_score >= 65:
        strong = {
            "Hisse": symbol.removesuffix(".IS"),
            "Aylık Sınıf": "Güçlü Trend" if strong_score >= 80 else "Trend Devamı",
            "Aylık Skor": strong_score,
            "Durum": "Henüz Validate Değil",
            "3A Excess %": round(100 * x["excess3"], 2) if pd.notna(x["excess3"]) else np.nan,
            "6A Excess %": round(100 * x["excess6"], 2) if pd.notna(x["excess6"]) else np.nan,
            "Direnç Uzaklığı %": round(x["dist"], 2) if pd.notna(x["dist"]) else np.nan,
            "RSI": round(x["rsi"], 2),
            "Hacim Oranı": round(x["vol_ratio"], 2) if pd.notna(x["vol_ratio"]) else np.nan,
            "ATR %": round(x["atr_pct"], 2) if pd.notna(x["atr_pct"]) else np.nan,
            "Ay": x["month"],
            "Neden seçildi?": " ".join(strong_reasons),
        }

    early_score = 0
    early_reasons: list[str] = []
    close_near_ema = x["close"] >= x["ema6"] * 0.97
    if close_near_ema:
        early_score += 15
        early_reasons.append("Fiyat aylık EMA6 çevresinde/üzerinde.")
    if x["ema6_slope3"] >= -0.01:
        early_score += 10
        early_reasons.append("Aylık trend eğimi artık belirgin biçimde aşağı değil.")
    if 45 <= x["rsi"] <= 68 and x["rsi_delta2"] > 0:
        early_score += 20
        early_reasons.append("Aylık RSI toparlanıyor.")
    if pd.notna(x["dist"]) and 0 <= x["dist"] <= 12:
        early_score += 20
        early_reasons.append("Ana aylık dirence %12 içinde.")
    if x["benchmark_available"] and x["excess3"] > 0:
        early_score += 15
        early_reasons.append("3 aylık göreli güç XU100'e karşı iyileşiyor.")
    if pd.notna(x["vol_ratio"]) and x["vol_ratio"] >= 0.9:
        early_score += 10
        early_reasons.append("Aylık hacim davranışı zayıf değil.")
    if x["higher_low"]:
        early_score += 10
        early_reasons.append("Erken higher-low yapısı oluşuyor.")

    early = None
    already_strong = strong_score >= 65
    if early_score >= 60 and not already_strong:
        early = {
            "Hisse": symbol.removesuffix(".IS"),
            "Aylık Sınıf": "Yeni Trend Adayı" if early_score >= 75 else "Erken Dönüş / Birikim",
            "Aylık Skor": early_score,
            "Durum": "Henüz Validate Değil",
            "3A Excess %": round(100 * x["excess3"], 2) if pd.notna(x["excess3"]) else np.nan,
            "6A Excess %": round(100 * x["excess6"], 2) if pd.notna(x["excess6"]) else np.nan,
            "Direnç Uzaklığı %": round(x["dist"], 2) if pd.notna(x["dist"]) else np.nan,
            "RSI": round(x["rsi"], 2),
            "Hacim Oranı": round(x["vol_ratio"], 2) if pd.notna(x["vol_ratio"]) else np.nan,
            "ATR %": round(x["atr_pct"], 2) if pd.notna(x["atr_pct"]) else np.nan,
            "Ay": x["month"],
            "Neden seçildi?": " ".join(early_reasons),
        }
    return strong, early


def run_opportunity_radar(*, result_limit: int = 50) -> OpportunityRadarResult:
    edges, profiles = _load_validated_profiles()
    monthly_edges, monthly_profiles = _load_monthly_validated_profiles()
    universe = on_yukselis_evrenini_yukle(
        "BIST Tüm",
        internetten_guncelle=False,
    )

    # Tek veri hatti: mevcut batch market data seam. 420 completed days gives
    # enough current weekly/monthly structure while keeping newer listings eligible.
    batch = toplu_fiyat_verisi_getir(
        universe.semboller,
        islem_gunu=420,
        indirme_donemi="2y",
        parca_boyutu=40,
    )

    benchmark: pd.DataFrame | None
    try:
        benchmark = fiyat_verisi_getir(
            "XU100.IS",
            islem_gunu=420,
            indirme_donemi="2y",
            yalnizca_tamamlanmis_gunler=True,
        )
    except Exception:
        benchmark = None

    weekly_rows: list[dict[str, object]] = []
    strong_rows: list[dict[str, object]] = []
    early_rows: list[dict[str, object]] = []

    for symbol, daily in batch.veriler.items():
        try:
            row = _weekly_row(symbol, daily, edges, profiles)
            if row is not None:
                weekly_rows.append(row)
        except Exception:
            pass

        try:
            strong, early = _monthly_rows(symbol, daily, benchmark)
            if strong is not None:
                strong_rows.append(strong)
            if early is not None:
                early_rows.append(early)
        except Exception:
            pass

    weekly = pd.DataFrame(weekly_rows)
    if not weekly.empty:
        weekly["_validated"] = (weekly["Durum"] == "Validated").astype(int)
        weekly = weekly.sort_values(
            ["_validated", "Validated Profile Count", "Validated Quality", "Weekly Score"],
            ascending=[False, False, False, False],
        ).drop(columns=["_validated"]).reset_index(drop=True)
        weekly.insert(0, "Validated Öncelik", np.arange(1, len(weekly) + 1))
        weekly = weekly.head(result_limit).copy()

    monthly_strong = pd.DataFrame(strong_rows)
    if not monthly_strong.empty:
        monthly_strong = monthly_strong.sort_values(
            ["Aylık Skor", "6A Excess %", "3A Excess %"],
            ascending=[False, False, False],
        ).reset_index(drop=True)

    monthly_early = pd.DataFrame(early_rows)
    if not monthly_early.empty:
        monthly_early = monthly_early.sort_values(
            ["Aylık Skor", "3A Excess %", "6A Excess %"],
            ascending=[False, False, False],
        ).reset_index(drop=True)

    monthly_symbols = set()
    if not monthly_strong.empty:
        monthly_symbols.update(str(x) for x in monthly_strong["Hisse"])
    if not monthly_early.empty:
        monthly_symbols.update(str(x) for x in monthly_early["Hisse"])

    validation_data = {}
    if monthly_symbols:
        try:
            monthly_batch = toplu_fiyat_verisi_getir(
                [s if s.endswith(".IS") else s + ".IS" for s in sorted(monthly_symbols)],
                islem_gunu=1250,
                indirme_donemi="5y",
                parca_boyutu=40,
            )
            validation_data = dict(monthly_batch.veriler)
        except Exception:
            validation_data = {}

    monthly_strong = _apply_monthly_validation(
        monthly_strong, validation_data, monthly_edges, monthly_profiles
    )
    monthly_early = _apply_monthly_validation(
        monthly_early, validation_data, monthly_edges, monthly_profiles
    )

    for frame in (monthly_strong, monthly_early):
        if not frame.empty:
            frame["_validation_priority"] = frame["Durum"].map(
                {"Validated Profile Match": 2, "Ay İçi Geçici Match": 1}
            ).fillna(0)
            frame.sort_values(
                ["_validation_priority", "Profile Match Count", "Validated Quality", "Aylık Skor"],
                ascending=[False, False, False, False],
                inplace=True,
            )
            frame.drop(columns=["_validation_priority"], inplace=True)
            frame.reset_index(drop=True, inplace=True)

    monthly_strong = monthly_strong.head(result_limit).reset_index(drop=True)
    monthly_early = monthly_early.head(result_limit).reset_index(drop=True)

    return OpportunityRadarResult(
        universe_name=universe.ad,
        universe_source=universe.kaynak,
        universe_date=universe.tarih,
        universe_count=len(universe.semboller),
        data_success_count=len(batch.veriler),
        data_failures=batch.hatalar,
        weekly=weekly,
        monthly_strong=monthly_strong,
        monthly_early=monthly_early,
    )
