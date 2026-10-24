from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from math import ceil, isfinite
from statistics import median
from typing import Callable, Iterable

import pandas as pd

from backend.app.analysis.bist_universe import (
    BistUniverse,
    BistUniverseError,
    BistUniverseRepository,
)
from backend.app.data.market_data import fiyat_verisi_getir
from backend.app.indicators.technical_indicators import ema, macd, rsi


class SectorMemberStrengthError(RuntimeError):
    """Sektör üyesi hisselerden güvenilir bağlam üretilemediğinde kullanılır."""


@dataclass(frozen=True, slots=True)
class SectorMemberDefinition:
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class SectorMemberStrengthResult:
    rank: int
    code: str
    name: str
    analysis_date: date
    member_count: int
    valid_member_count: int
    coverage_ratio: float
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
    positive_1d_ratio: float
    positive_5d_ratio: float
    above_ema21_ratio: float
    short_trend_ratio: float
    momentum_positive_ratio: float
    median_volume_ratio: float | None
    relative_score: int
    trend_score: int
    momentum_score: int
    participation_score: int
    strength_score: int
    status: str
    confidence: str


@dataclass(frozen=True, slots=True)
class SectorMemberStrengthMap:
    reference_universe: str
    benchmark_symbol: str
    analysis_date: date
    items: tuple[SectorMemberStrengthResult, ...]
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _MemberMetrics:
    return_1d: float
    return_5d: float
    return_20d: float
    positive_1d: bool
    positive_5d: bool
    above_ema21: bool
    short_trend_positive: bool
    momentum_positive: bool
    volume_ratio: float | None


MarketDataLoader = Callable[..., pd.DataFrame]


DEFAULT_MEMBER_SECTORS: tuple[SectorMemberDefinition, ...] = (
    SectorMemberDefinition("XBANK", "Bankacılık"),
    SectorMemberDefinition("XUSIN", "Sınai"),
    SectorMemberDefinition("XUHIZ", "Hizmetler"),
    SectorMemberDefinition("XUMAL", "Mali"),
    SectorMemberDefinition("XUTEK", "Teknoloji"),
    SectorMemberDefinition("XHOLD", "Holding ve Yatırım"),
    SectorMemberDefinition("XULAS", "Ulaştırma"),
    SectorMemberDefinition("XGIDA", "Gıda ve İçecek"),
    SectorMemberDefinition("XTRZM", "Turizm"),
    SectorMemberDefinition("XELKT", "Elektrik"),
    SectorMemberDefinition("XILTM", "İletişim"),
    SectorMemberDefinition("XKMYA", "Kimya Petrol Plastik"),
    SectorMemberDefinition("XMADN", "Madencilik"),
    SectorMemberDefinition("XSGRT", "Sigorta"),
    SectorMemberDefinition("XTCRT", "Toptan ve Perakende Ticaret"),
)

BENCHMARK_SYMBOL = "XU100.IS"


def _load_frame(
    symbol: str,
    *,
    loader: MarketDataLoader,
    bars: int,
    minimum_bars: int = 60,
) -> pd.DataFrame:
    try:
        frame = loader(
            symbol,
            islem_gunu=bars,
            indirme_donemi="1y",
            yalnizca_tamamlanmis_gunler=True,
        )
    except TypeError:
        frame = loader(symbol)

    if frame is None or frame.empty:
        raise SectorMemberStrengthError(
            f"{symbol} için piyasa verisi bulunamadı."
        )

    if "Close" not in frame.columns:
        raise SectorMemberStrengthError(
            f"{symbol} için Close sütunu bulunamadı."
        )

    clean = frame.copy()
    clean.index = pd.to_datetime(clean.index)
    clean = clean.sort_index()
    clean["Close"] = pd.to_numeric(clean["Close"], errors="coerce")
    if "Volume" not in clean.columns:
        clean["Volume"] = 0.0
    clean["Volume"] = pd.to_numeric(clean["Volume"], errors="coerce")
    clean = clean.dropna(subset=["Close"])
    clean = clean[clean["Close"] > 0]

    if len(clean) < minimum_bars:
        raise SectorMemberStrengthError(
            f"{symbol} için en az {minimum_bars} günlük bar gerekir; "
            f"bulunan: {len(clean)}."
        )

    return clean


def _return_percent(close: pd.Series, periods: int) -> float:
    if len(close) <= periods:
        raise SectorMemberStrengthError(
            f"{periods} günlük getiri için yeterli veri yok."
        )

    start = float(close.iloc[-(periods + 1)])
    end = float(close.iloc[-1])
    if (
        start <= 0
        or not isfinite(start)
        or not isfinite(end)
    ):
        raise SectorMemberStrengthError(
            "Getiri hesabında geçersiz kapanış fiyatı bulundu."
        )

    return ((end / start) - 1.0) * 100.0


def _member_metrics(frame: pd.DataFrame) -> _MemberMetrics:
    close = frame["Close"]
    return_1d = _return_percent(close, 1)
    return_5d = _return_percent(close, 5)
    return_20d = _return_percent(close, 20)

    e9 = ema(close, 9)
    e21 = ema(close, 21)
    rsi14 = rsi(close, 14)
    macd_frame = macd(close)

    current_close = float(close.iloc[-1])
    ema9_value = float(e9.iloc[-1])
    ema21_value = float(e21.iloc[-1])
    rsi_value = float(rsi14.iloc[-1])
    macd_value = float(macd_frame["MACD"].iloc[-1])
    signal_value = float(macd_frame["MACD_Sinyal"].iloc[-1])
    histogram_value = float(macd_frame["MACD_Histogram"].iloc[-1])

    volume = pd.to_numeric(frame["Volume"], errors="coerce")
    current_volume = (
        float(volume.iloc[-1])
        if len(volume) and pd.notna(volume.iloc[-1])
        else 0.0
    )
    average_volume = float(volume.tail(20).mean())
    volume_ratio: float | None = None
    if (
        current_volume > 0
        and average_volume > 0
        and isfinite(current_volume)
        and isfinite(average_volume)
    ):
        volume_ratio = current_volume / average_volume

    return _MemberMetrics(
        return_1d=return_1d,
        return_5d=return_5d,
        return_20d=return_20d,
        positive_1d=return_1d > 0,
        positive_5d=return_5d > 0,
        above_ema21=current_close > ema21_value,
        short_trend_positive=ema9_value > ema21_value,
        momentum_positive=(
            rsi_value >= 50
            and macd_value > signal_value
            and histogram_value > 0
        ),
        volume_ratio=volume_ratio,
    )


def _relative_score(
    relative_1d: float,
    relative_5d: float,
    relative_20d: float,
) -> int:
    return (
        (10 if relative_1d > 0 else 0)
        + (15 if relative_5d > 0 else 0)
        + (15 if relative_20d > 0 else 0)
    )


def _status(score: int) -> str:
    if score >= 70:
        return "Güçlü"
    if score >= 55:
        return "Pozitif"
    if score >= 40:
        return "Nötr"
    return "Zayıf"


def _aggregate_sector(
    definition: SectorMemberDefinition,
    *,
    members: tuple[str, ...],
    benchmark_frame: pd.DataFrame,
    loader: MarketDataLoader,
    frame_cache: dict[str, pd.DataFrame | Exception],
    bars: int,
    minimum_members: int,
    minimum_coverage: float,
) -> SectorMemberStrengthResult:
    benchmark_date = pd.Timestamp(benchmark_frame.index[-1]).date()
    metrics: list[_MemberMetrics] = []

    for symbol in members:
        cached = frame_cache.get(symbol)
        if cached is None:
            try:
                cached = _load_frame(
                    symbol,
                    loader=loader,
                    bars=bars,
                )
            except Exception as exc:
                cached = exc
            frame_cache[symbol] = cached

        if isinstance(cached, Exception):
            continue

        if pd.Timestamp(cached.index[-1]).date() != benchmark_date:
            continue

        try:
            metrics.append(_member_metrics(cached))
        except Exception:
            continue

    total = len(members)
    valid = len(metrics)
    coverage = (valid / total) if total else 0.0

    # BIST 100 kesişiminde bazı gerçek sektörlerin doğal olarak yalnızca
    # iki üyesi bulunabilir. Böyle bir sektörü 2/2 güncel olduğunda tamamen
    # kaybetmek yerine "Düşük" güvenle bağlam olarak tutuyoruz.
    # Tek üyeli sektörler sektör temsili sayılmaz.
    if total <= 1:
        raise SectorMemberStrengthError(
            f"{definition.code} için sektör temsili yetersiz: "
            f"{total} referans üye."
        )

    if total == 2:
        required = 2
        confidence = "Düşük"
    else:
        required = max(
            minimum_members,
            ceil(total * minimum_coverage),
        )
        confidence = (
            "Yüksek"
            if coverage >= 0.80 and valid >= 5
            else "Orta"
        )

    if valid < required:
        raise SectorMemberStrengthError(
            f"{definition.code} için temsil gücü yetersiz: "
            f"{valid}/{total} güncel üye; gereken en az {required}."
        )

    return_1d = float(median(m.return_1d for m in metrics))
    return_5d = float(median(m.return_5d for m in metrics))
    return_20d = float(median(m.return_20d for m in metrics))

    benchmark_close = benchmark_frame["Close"]
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

    positive_1d_ratio = sum(m.positive_1d for m in metrics) / valid
    positive_5d_ratio = sum(m.positive_5d for m in metrics) / valid
    above_ema21_ratio = sum(m.above_ema21 for m in metrics) / valid
    short_trend_ratio = (
        sum(m.short_trend_positive for m in metrics) / valid
    )
    momentum_positive_ratio = (
        sum(m.momentum_positive for m in metrics) / valid
    )

    volume_values = [
        m.volume_ratio
        for m in metrics
        if m.volume_ratio is not None
    ]
    median_volume_ratio = (
        float(median(volume_values))
        if volume_values
        else None
    )

    relative_score = _relative_score(
        relative_1d,
        relative_5d,
        relative_20d,
    )
    trend_score = int(
        round(
            15 * above_ema21_ratio
            + 10 * short_trend_ratio
        )
    )
    momentum_score = int(
        round(
            10 * positive_5d_ratio
            + 10 * momentum_positive_ratio
        )
    )

    volume_component = 0.5
    if median_volume_ratio is not None:
        volume_component = min(
            max(median_volume_ratio / 1.20, 0.0),
            1.0,
        )

    participation_score = int(
        round(
            10 * positive_1d_ratio
            + 5 * volume_component
        )
    )

    strength_score = max(
        0,
        min(
            100,
            relative_score
            + trend_score
            + momentum_score
            + participation_score,
        ),
    )

    return SectorMemberStrengthResult(
        rank=0,
        code=definition.code,
        name=definition.name,
        analysis_date=benchmark_date,
        member_count=total,
        valid_member_count=valid,
        coverage_ratio=coverage,
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
        positive_1d_ratio=positive_1d_ratio,
        positive_5d_ratio=positive_5d_ratio,
        above_ema21_ratio=above_ema21_ratio,
        short_trend_ratio=short_trend_ratio,
        momentum_positive_ratio=momentum_positive_ratio,
        median_volume_ratio=median_volume_ratio,
        relative_score=relative_score,
        trend_score=trend_score,
        momentum_score=momentum_score,
        participation_score=participation_score,
        strength_score=strength_score,
        status=_status(strength_score),
        confidence=confidence,
    )


def build_sector_member_strength_map(
    *,
    sectors: Iterable[SectorMemberDefinition] = DEFAULT_MEMBER_SECTORS,
    reference_universe: str = "BIST 100",
    benchmark_symbol: str = BENCHMARK_SYMBOL,
    repository: BistUniverseRepository | None = None,
    loader: MarketDataLoader = fiyat_verisi_getir,
    bars: int = 90,
    minimum_members: int = 3,
    minimum_coverage: float = 0.60,
    refresh_membership: bool = True,
) -> SectorMemberStrengthMap:
    """
    Sektör gücünü Yahoo sektör endekslerinden değil, resmî BIST sektör
    üyelikleri ve üyelerin gerçek fiyatlarından üretir.

    Varsayılan olarak sektör üyeleri BIST 100 ile kesiştirilir. Böylece
    BIST 100 aday taramasında kullanılan bağlam, aynı yatırım evreninden
    üretilir. Sonuç bir hard filtre değildir.
    """
    if bars < 60:
        raise ValueError("Sektör üye analizi için en az 60 bar istenmelidir.")
    if minimum_members < 1:
        raise ValueError("minimum_members en az 1 olmalıdır.")
    if not 0 < minimum_coverage <= 1:
        raise ValueError("minimum_coverage 0 ile 1 arasında olmalıdır.")

    repo = repository or BistUniverseRepository()

    try:
        reference = repo.evreni_yukle(
            reference_universe,
            internetten_guncelle=refresh_membership,
        )
    except (ValueError, BistUniverseError) as exc:
        raise SectorMemberStrengthError(
            f"{reference_universe} üyeleri yüklenemedi: {exc}"
        ) from exc

    reference_symbols = set(reference.semboller)

    benchmark_frame = _load_frame(
        benchmark_symbol,
        loader=loader,
        bars=bars,
    )
    benchmark_date = pd.Timestamp(benchmark_frame.index[-1]).date()

    frame_cache: dict[str, pd.DataFrame | Exception] = {}
    results: list[SectorMemberStrengthResult] = []
    errors: list[str] = []

    for definition in tuple(sectors):
        try:
            sector_universe = repo.endeks_bilesenlerini_yukle(
                definition.code,
                endeks_adi=definition.name,
                # Referans evreni yükleme adımı güncel dosyayı cache'e yazdı.
                # Aynı çalışmada her sektör için yeniden internet çağrısı yapma.
                internetten_guncelle=False,
            )
            members = tuple(
                symbol
                for symbol in sector_universe.semboller
                if symbol in reference_symbols
            )
            if not members:
                raise SectorMemberStrengthError(
                    f"{reference_universe} referans evreninde üye yok."
                )

            results.append(
                _aggregate_sector(
                    definition,
                    members=members,
                    benchmark_frame=benchmark_frame,
                    loader=loader,
                    frame_cache=frame_cache,
                    bars=bars,
                    minimum_members=minimum_members,
                    minimum_coverage=minimum_coverage,
                )
            )
        except (
            BistUniverseError,
            SectorMemberStrengthError,
            ValueError,
        ) as exc:
            errors.append(f"{definition.code}: {exc}")
        except Exception as exc:
            errors.append(
                f"{definition.code}: Beklenmeyen sektör analizi hatası: {exc}"
            )

    if not results:
        raise SectorMemberStrengthError(
            "Hiçbir sektör için üye-hisse tabanlı güç sonucu üretilemedi."
        )

    ordered = sorted(
        results,
        key=lambda item: (
            item.strength_score,
            item.relative_composite,
            item.coverage_ratio,
        ),
        reverse=True,
    )
    ranked = tuple(
        replace(item, rank=rank)
        for rank, item in enumerate(ordered, start=1)
    )

    return SectorMemberStrengthMap(
        reference_universe=reference_universe,
        benchmark_symbol=benchmark_symbol,
        analysis_date=benchmark_date,
        items=ranked,
        errors=tuple(errors),
    )


def sector_member_strength_rows(
    result: SectorMemberStrengthMap,
) -> tuple[dict[str, object], ...]:
    """Dashboard/CSV için sade, sinyal üretmeyen sektör bağlam satırları."""
    rows: list[dict[str, object]] = []

    for item in result.items:
        rows.append(
            {
                "Sıra": item.rank,
                "Sektör": item.name,
                "Endeks": item.code,
                "Skor": item.strength_score,
                "Durum": item.status,
                "Güven": item.confidence,
                "Üye": item.member_count,
                "Güncel üye": item.valid_member_count,
                "Kapsama (%)": round(item.coverage_ratio * 100, 1),
                "1G medyan (%)": round(item.return_1d, 2),
                "5G medyan (%)": round(item.return_5d, 2),
                "20G medyan (%)": round(item.return_20d, 2),
                "RS 1G": round(item.relative_1d, 2),
                "RS 5G": round(item.relative_5d, 2),
                "RS 20G": round(item.relative_20d, 2),
                "Bileşik RS": round(item.relative_composite, 2),
                "1G pozitif (%)": round(item.positive_1d_ratio * 100, 1),
                "EMA21 üstü (%)": round(item.above_ema21_ratio * 100, 1),
                "Kısa trend + (%)": round(item.short_trend_ratio * 100, 1),
                "Momentum + (%)": round(
                    item.momentum_positive_ratio * 100,
                    1,
                ),
                "Medyan hacim": (
                    round(item.median_volume_ratio, 2)
                    if item.median_volume_ratio is not None
                    else None
                ),
                "Tarih": item.analysis_date.isoformat(),
            }
        )

    return tuple(rows)
