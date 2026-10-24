from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from math import isfinite
from typing import Callable, Iterable

import pandas as pd

from backend.app.data.market_data import fiyat_verisi_getir
from backend.app.indicators.technical_indicators import ema, macd, rsi


class SectorMarketStrengthError(RuntimeError):
    """Sektörel piyasa gücü güvenle üretilemediğinde kullanılır."""


@dataclass(frozen=True, slots=True)
class SectorIndexDefinition:
    code: str
    name: str
    yahoo_symbol: str


@dataclass(frozen=True, slots=True)
class SectorMarketStrengthResult:
    rank: int
    code: str
    name: str
    yahoo_symbol: str
    analysis_date: date
    close: float
    return_1d: float
    return_5d: float
    return_20d: float
    benchmark_return_1d: float
    benchmark_return_5d: float
    benchmark_return_20d: float
    relative_1d: float
    relative_5d: float
    relative_20d: float
    relative_composite: float
    relative_score: int
    trend_score: int
    momentum_score: int
    volume_score: int
    strength_score: int
    status: str
    trend_status: str
    momentum_status: str
    volume_ratio: float | None
    volume_available: bool


@dataclass(frozen=True, slots=True)
class SectorMarketMap:
    benchmark_symbol: str
    analysis_date: date
    items: tuple[SectorMarketStrengthResult, ...]
    errors: tuple[str, ...] = ()


MarketDataLoader = Callable[..., pd.DataFrame]


# Borsa İstanbul'un yerleşik sektör endekslerinden, kısa vadeli aday
# değerlendirmesinde en çok kullanılacak çekirdek set.
DEFAULT_SECTOR_INDICES: tuple[SectorIndexDefinition, ...] = (
    SectorIndexDefinition("XBANK", "Bankacılık", "XBANK.IS"),
    SectorIndexDefinition("XUSIN", "Sınai", "XUSIN.IS"),
    SectorIndexDefinition("XUHIZ", "Hizmetler", "XUHIZ.IS"),
    SectorIndexDefinition("XUMAL", "Mali", "XUMAL.IS"),
    SectorIndexDefinition("XUTEK", "Teknoloji", "XUTEK.IS"),
    SectorIndexDefinition("XHOLD", "Holding ve Yatırım", "XHOLD.IS"),
    SectorIndexDefinition("XULAS", "Ulaştırma", "XULAS.IS"),
    SectorIndexDefinition("XGIDA", "Gıda ve İçecek", "XGIDA.IS"),
    SectorIndexDefinition("XTRZM", "Turizm", "XTRZM.IS"),
    SectorIndexDefinition("XELKT", "Elektrik", "XELKT.IS"),
    SectorIndexDefinition("XILTM", "İletişim", "XILTM.IS"),
    SectorIndexDefinition("XKMYA", "Kimya Petrol Plastik", "XKMYA.IS"),
    SectorIndexDefinition("XMADN", "Madencilik", "XMADN.IS"),
    SectorIndexDefinition("XSGRT", "Sigorta", "XSGRT.IS"),
    SectorIndexDefinition("XTCRT", "Toptan ve Perakende Ticaret", "XTCRT.IS"),
)

BENCHMARK_SYMBOL = "XU100.IS"


def _load_frame(
    symbol: str,
    *,
    loader: MarketDataLoader,
    bars: int,
) -> pd.DataFrame:
    try:
        frame = loader(
            symbol,
            islem_gunu=bars,
            indirme_donemi="1y",
            yalnizca_tamamlanmis_gunler=True,
        )
    except TypeError:
        # Test/alternatif yükleyicilerin sade imzasını da destekler.
        frame = loader(symbol)

    if frame is None or frame.empty:
        raise SectorMarketStrengthError(
            f"{symbol} için piyasa verisi bulunamadı."
        )

    required = {"Close", "Volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise SectorMarketStrengthError(
            f"{symbol} için eksik sütunlar: {', '.join(sorted(missing))}"
        )

    clean = frame.copy()
    clean.index = pd.to_datetime(clean.index)
    clean = clean.sort_index()
    clean["Close"] = pd.to_numeric(clean["Close"], errors="coerce")
    clean["Volume"] = pd.to_numeric(clean["Volume"], errors="coerce")
    clean = clean.dropna(subset=["Close"])
    clean = clean[clean["Close"] > 0]

    if len(clean) < 60:
        raise SectorMarketStrengthError(
            f"{symbol} için en az 60 günlük bar gerekir; bulunan: {len(clean)}."
        )

    return clean


def _return_percent(close: pd.Series, periods: int) -> float:
    if len(close) <= periods:
        raise SectorMarketStrengthError(
            f"{periods} günlük getiri için yeterli veri yok."
        )

    start = float(close.iloc[-(periods + 1)])
    end = float(close.iloc[-1])

    if start <= 0 or not isfinite(start) or not isfinite(end):
        raise SectorMarketStrengthError(
            "Getiri hesabında geçersiz kapanış fiyatı bulundu."
        )

    return ((end / start) - 1.0) * 100.0


def _align_close(
    sector: pd.DataFrame,
    benchmark: pd.DataFrame,
) -> tuple[pd.Series, pd.Series]:
    aligned = pd.concat(
        (
            sector["Close"].rename("sector"),
            benchmark["Close"].rename("benchmark"),
        ),
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) < 60:
        raise SectorMarketStrengthError(
            "Sektör ve XU100 için en az 60 ortak işlem günü gerekir."
        )

    return aligned["sector"], aligned["benchmark"]


def _relative_score(
    relative_1d: float,
    relative_5d: float,
    relative_20d: float,
) -> int:
    # Göreceli güç burada bir hard filter değildir. Her pozitif dönem,
    # sektörün XU100'e göre üstün performansını kademeli olarak ödüllendirir.
    return (
        (10 if relative_1d > 0 else 0)
        + (15 if relative_5d > 0 else 0)
        + (15 if relative_20d > 0 else 0)
    )


def _trend_metrics(frame: pd.DataFrame) -> tuple[int, str]:
    close = frame["Close"]
    e9 = ema(close, 9)
    e21 = ema(close, 21)
    e55 = ema(close, 55)

    c = float(close.iloc[-1])
    v9 = float(e9.iloc[-1])
    v21 = float(e21.iloc[-1])
    v55 = float(e55.iloc[-1])

    score = 0
    if c > v21:
        score += 10
    if v9 > v21:
        score += 10
    if v21 > v55:
        score += 10

    if score >= 30:
        status = "Pozitif"
    elif score <= 10:
        status = "Negatif"
    else:
        status = "Nötr"

    return score, status


def _momentum_metrics(frame: pd.DataFrame) -> tuple[int, str]:
    close = frame["Close"]
    rsi14 = rsi(close, 14)
    macd_frame = macd(close)

    rsi_value = float(rsi14.iloc[-1])
    macd_value = float(macd_frame["MACD"].iloc[-1])
    signal_value = float(macd_frame["MACD_Sinyal"].iloc[-1])
    histogram_value = float(macd_frame["MACD_Histogram"].iloc[-1])

    score = 0
    if 50 <= rsi_value <= 70:
        score += 8
    elif rsi_value > 70:
        # Güçlü momentum var, ancak aşırı ısınma ihtimali nedeniyle tam puan değil.
        score += 5

    if macd_value > signal_value:
        score += 8
    if histogram_value > 0:
        score += 4

    if score >= 16:
        status = "Pozitif"
    elif score <= 4:
        status = "Negatif"
    else:
        status = "Nötr"

    return score, status


def _volume_metrics(frame: pd.DataFrame) -> tuple[int, float | None, bool]:
    volume = pd.to_numeric(frame["Volume"], errors="coerce")
    current = float(volume.iloc[-1]) if pd.notna(volume.iloc[-1]) else 0.0
    average = float(volume.tail(20).mean())

    if (
        current <= 0
        or average <= 0
        or not isfinite(current)
        or not isfinite(average)
    ):
        # Sektör endekslerinde hacim her sağlayıcıda güvenilir olmayabilir.
        # Eksik hacim, sektörün diğer teknik verilerini geçersiz kılmaz.
        return 5, None, False

    ratio = current / average
    if ratio >= 1.20:
        score = 10
    elif ratio >= 1.00:
        score = 7
    elif ratio >= 0.80:
        score = 5
    else:
        score = 2

    return score, ratio, True


def _status(strength_score: int) -> str:
    if strength_score >= 70:
        return "Güçlü"
    if strength_score >= 55:
        return "Pozitif"
    if strength_score >= 40:
        return "Nötr"
    return "Zayıf"


def analyze_sector_index(
    definition: SectorIndexDefinition,
    *,
    benchmark_frame: pd.DataFrame,
    loader: MarketDataLoader = fiyat_verisi_getir,
    bars: int = 90,
) -> SectorMarketStrengthResult:
    """Tek bir sektör endeksini XU100'e göre değerlendirir.

    Sonuç yalnızca sektör bağlamı ve göreceli güç üretir.
    Alım/satım sinyali veya hard aday filtresi üretmez.
    """

    sector_frame = _load_frame(
        definition.yahoo_symbol,
        loader=loader,
        bars=bars,
    )

    benchmark_last = pd.Timestamp(benchmark_frame.index[-1]).date()
    sector_last = pd.Timestamp(sector_frame.index[-1]).date()

    if sector_last != benchmark_last:
        raise SectorMarketStrengthError(
            f"{definition.code} son veri tarihi {sector_last}; "
            f"XU100 tarihi {benchmark_last}. Güncel sektör karşılaştırması yapılamadı."
        )

    sector_close, benchmark_close = _align_close(
        sector_frame,
        benchmark_frame,
    )

    return_1d = _return_percent(sector_close, 1)
    return_5d = _return_percent(sector_close, 5)
    return_20d = _return_percent(sector_close, 20)

    benchmark_return_1d = _return_percent(benchmark_close, 1)
    benchmark_return_5d = _return_percent(benchmark_close, 5)
    benchmark_return_20d = _return_percent(benchmark_close, 20)

    relative_1d = return_1d - benchmark_return_1d
    relative_5d = return_5d - benchmark_return_5d
    relative_20d = return_20d - benchmark_return_20d

    relative_composite = (
        relative_1d * 0.20
        + relative_5d * 0.35
        + relative_20d * 0.45
    )

    relative_score = _relative_score(
        relative_1d,
        relative_5d,
        relative_20d,
    )
    trend_score, trend_status = _trend_metrics(sector_frame)
    momentum_score, momentum_status = _momentum_metrics(sector_frame)
    volume_score, volume_ratio, volume_available = _volume_metrics(
        sector_frame
    )

    strength_score = int(
        relative_score
        + trend_score
        + momentum_score
        + volume_score
    )

    return SectorMarketStrengthResult(
        rank=0,
        code=definition.code,
        name=definition.name,
        yahoo_symbol=definition.yahoo_symbol,
        analysis_date=sector_last,
        close=float(sector_frame["Close"].iloc[-1]),
        return_1d=return_1d,
        return_5d=return_5d,
        return_20d=return_20d,
        benchmark_return_1d=benchmark_return_1d,
        benchmark_return_5d=benchmark_return_5d,
        benchmark_return_20d=benchmark_return_20d,
        relative_1d=relative_1d,
        relative_5d=relative_5d,
        relative_20d=relative_20d,
        relative_composite=relative_composite,
        relative_score=relative_score,
        trend_score=trend_score,
        momentum_score=momentum_score,
        volume_score=volume_score,
        strength_score=strength_score,
        status=_status(strength_score),
        trend_status=trend_status,
        momentum_status=momentum_status,
        volume_ratio=volume_ratio,
        volume_available=volume_available,
    )


def build_sector_market_map(
    *,
    sectors: Iterable[SectorIndexDefinition] = DEFAULT_SECTOR_INDICES,
    benchmark_symbol: str = BENCHMARK_SYMBOL,
    loader: MarketDataLoader = fiyat_verisi_getir,
    bars: int = 90,
) -> SectorMarketMap:
    """Sektörleri teknik güç ve XU100'e göre göreceli güçle sıralar."""

    if bars < 60:
        raise ValueError("Sektör analizi için en az 60 bar istenmelidir.")

    benchmark_frame = _load_frame(
        benchmark_symbol,
        loader=loader,
        bars=bars,
    )
    benchmark_date = pd.Timestamp(
        benchmark_frame.index[-1]
    ).date()

    raw_results: list[SectorMarketStrengthResult] = []
    errors: list[str] = []

    for definition in tuple(sectors):
        try:
            raw_results.append(
                analyze_sector_index(
                    definition,
                    benchmark_frame=benchmark_frame,
                    loader=loader,
                    bars=bars,
                )
            )
        except SectorMarketStrengthError as exc:
            errors.append(f"{definition.code}: {exc}")
        except Exception as exc:
            errors.append(
                f"{definition.code}: Beklenmeyen sektör veri hatası: {exc}"
            )

    if not raw_results:
        raise SectorMarketStrengthError(
            "Hiçbir sektör endeksi için güncel güç sonucu üretilemedi."
        )

    ordered = sorted(
        raw_results,
        key=lambda item: (
            item.strength_score,
            item.relative_composite,
        ),
        reverse=True,
    )

    ranked = tuple(
        replace(item, rank=rank)
        for rank, item in enumerate(ordered, start=1)
    )

    return SectorMarketMap(
        benchmark_symbol=benchmark_symbol,
        analysis_date=benchmark_date,
        items=ranked,
        errors=tuple(errors),
    )


def sector_market_rows(
    result: SectorMarketMap,
) -> tuple[dict[str, object], ...]:
    """Dashboard/CSV için sade sektör güç satırları üretir."""

    rows: list[dict[str, object]] = []

    for item in result.items:
        rows.append(
            {
                "Sıra": item.rank,
                "Sektör": item.name,
                "Endeks": item.code,
                "Skor": item.strength_score,
                "Durum": item.status,
                "1G (%)": round(item.return_1d, 2),
                "5G (%)": round(item.return_5d, 2),
                "20G (%)": round(item.return_20d, 2),
                "RS 1G": round(item.relative_1d, 2),
                "RS 5G": round(item.relative_5d, 2),
                "RS 20G": round(item.relative_20d, 2),
                "Bileşik RS": round(item.relative_composite, 2),
                "Trend": item.trend_status,
                "Momentum": item.momentum_status,
                "Hacim oranı": (
                    round(item.volume_ratio, 2)
                    if item.volume_ratio is not None
                    else None
                ),
                "Tarih": item.analysis_date.isoformat(),
            }
        )

    return tuple(rows)
