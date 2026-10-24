from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

import pandas as pd

from ..indicators.technical_indicators import teknik_gostergeleri_ekle


class DivergenceAnalysisError(ValueError):
    """RSI/MACD uyumsuzluk analizi üretilemedi."""


class DivergenceKind(str, Enum):
    NORMAL_POSITIVE = "Normal Pozitif"
    NORMAL_NEGATIVE = "Normal Negatif"
    HIDDEN_POSITIVE = "Gizli Pozitif"
    HIDDEN_NEGATIVE = "Gizli Negatif"


@dataclass(frozen=True)
class PivotPoint:
    position: int
    timestamp: pd.Timestamp
    price: float
    oscillator: float


@dataclass(frozen=True)
class DivergenceSignal:
    timeframe: str
    oscillator: str
    kind: DivergenceKind
    first: PivotPoint
    second: PivotPoint
    price_change_percent: float
    oscillator_change: float
    volume_confirmation: bool
    confidence_score: int
    confidence_level: str
    explanation: str


@dataclass(frozen=True)
class TimeframeDivergenceResult:
    timeframe: str
    latest_timestamp: pd.Timestamp
    signals: tuple[DivergenceSignal, ...]
    summary: str
    positive_count: int
    negative_count: int
    disclaimer: str = (
        "Uyumsuzluk tek başına alım/satım sinyali değildir; "
        "trend, hacim, destek/direnç ve risk koşullarıyla birlikte değerlendirilir."
    )


def _validate_frame(frame: pd.DataFrame) -> None:
    required = {"Close", "Volume"}
    missing = required - set(frame.columns)
    if missing:
        raise DivergenceAnalysisError(
            "Uyumsuzluk analizi için eksik sütunlar: "
            + ", ".join(sorted(missing))
        )
    if len(frame) < 45:
        raise DivergenceAnalysisError(
            "Uyumsuzluk analizi için en az 45 tamamlanmış bar gerekir."
        )
    if frame.index.has_duplicates:
        raise DivergenceAnalysisError(
            "Uyumsuzluk verisinde tekrarlanan zaman damgası var."
        )
    if not frame.index.is_monotonic_increasing:
        raise DivergenceAnalysisError(
            "Uyumsuzluk verisi tarih sırasına göre artan olmalıdır."
        )


def _pivot_positions(
    series: pd.Series,
    *,
    mode: str,
    left_bars: int,
    right_bars: int,
) -> tuple[int, ...]:
    positions: list[int] = []
    values = series.astype(float)

    for position in range(left_bars, len(values) - right_bars):
        value = values.iloc[position]
        if pd.isna(value):
            continue

        left = values.iloc[position - left_bars:position]
        right = values.iloc[position + 1:position + right_bars + 1]

        if left.isna().any() or right.isna().any():
            continue

        if mode == "low":
            confirmed = value < float(left.min()) and value <= float(right.min())
        elif mode == "high":
            confirmed = value > float(left.max()) and value >= float(right.max())
        else:
            raise DivergenceAnalysisError("Pivot türü geçersiz.")

        if confirmed:
            positions.append(position)

    return tuple(positions)


def _paired_pivots(
    frame: pd.DataFrame,
    oscillator_column: str,
    *,
    mode: str,
    left_bars: int,
    right_bars: int,
) -> tuple[PivotPoint, ...]:
    price_positions = _pivot_positions(
        frame["Close"],
        mode=mode,
        left_bars=left_bars,
        right_bars=right_bars,
    )
    oscillator = frame[oscillator_column].astype(float)

    points = []
    for position in price_positions:
        value = oscillator.iloc[position]
        if pd.isna(value):
            continue
        points.append(
            PivotPoint(
                position=position,
                timestamp=pd.Timestamp(frame.index[position]),
                price=float(frame["Close"].iloc[position]),
                oscillator=float(value),
            )
        )
    return tuple(points)


def _volume_confirmation(
    frame: pd.DataFrame,
    first_position: int,
    second_position: int,
    *,
    positive: bool,
) -> bool:
    volume = frame["Volume"].astype(float)
    average = volume.rolling(20, min_periods=10).mean()
    second_volume = float(volume.iloc[second_position])
    second_average = float(average.iloc[second_position])

    if pd.isna(second_average) or second_average <= 0:
        return False

    ratio = second_volume / second_average
    price_path = frame["Close"].iloc[first_position:second_position + 1]

    if positive:
        recovery = float(price_path.iloc[-1]) >= float(price_path.min()) * 1.01
        return ratio >= 1.05 or recovery

    rejection = float(price_path.iloc[-1]) <= float(price_path.max()) * 0.99
    return ratio >= 1.05 or rejection


def _confidence(
    *,
    price_change_percent: float,
    oscillator_change: float,
    bar_distance: int,
    volume_confirmation: bool,
    oscillator: str,
) -> tuple[int, str]:
    score = 35
    score += min(20, int(abs(price_change_percent) * 3))
    score += min(
        20,
        int(abs(oscillator_change) * (1.2 if oscillator == "RSI14" else 8)),
    )
    if 5 <= bar_distance <= 35:
        score += 10
    if volume_confirmation:
        score += 15

    score = max(0, min(100, score))
    if score >= 80:
        level = "Yüksek"
    elif score >= 60:
        level = "Orta"
    else:
        level = "Düşük"
    return score, level


def _classify_pair(
    first: PivotPoint,
    second: PivotPoint,
    *,
    mode: str,
    minimum_price_change_percent: float,
    minimum_oscillator_change: float,
) -> DivergenceKind | None:
    price_change = ((second.price / first.price) - 1.0) * 100.0
    oscillator_change = second.oscillator - first.oscillator

    if mode == "low":
        if (
            price_change <= -minimum_price_change_percent
            and oscillator_change >= minimum_oscillator_change
        ):
            return DivergenceKind.NORMAL_POSITIVE
        if (
            price_change >= minimum_price_change_percent
            and oscillator_change <= -minimum_oscillator_change
        ):
            return DivergenceKind.HIDDEN_POSITIVE

    if mode == "high":
        if (
            price_change >= minimum_price_change_percent
            and oscillator_change <= -minimum_oscillator_change
        ):
            return DivergenceKind.NORMAL_NEGATIVE
        if (
            price_change <= -minimum_price_change_percent
            and oscillator_change >= minimum_oscillator_change
        ):
            return DivergenceKind.HIDDEN_NEGATIVE

    return None


def _signals_for_oscillator(
    frame: pd.DataFrame,
    *,
    timeframe: str,
    oscillator_column: str,
    left_bars: int,
    right_bars: int,
    minimum_bar_distance: int,
    maximum_bar_distance: int,
    minimum_price_change_percent: float,
    minimum_oscillator_change: float,
    recent_bar_limit: int,
) -> tuple[DivergenceSignal, ...]:
    signals: list[DivergenceSignal] = []

    for mode in ("low", "high"):
        pivots = _paired_pivots(
            frame,
            oscillator_column,
            mode=mode,
            left_bars=left_bars,
            right_bars=right_bars,
        )

        for first, second in zip(pivots, pivots[1:]):
            distance = second.position - first.position
            if distance < minimum_bar_distance or distance > maximum_bar_distance:
                continue
            if len(frame) - 1 - second.position > recent_bar_limit:
                continue

            kind = _classify_pair(
                first,
                second,
                mode=mode,
                minimum_price_change_percent=minimum_price_change_percent,
                minimum_oscillator_change=minimum_oscillator_change,
            )
            if kind is None:
                continue

            positive = kind in {
                DivergenceKind.NORMAL_POSITIVE,
                DivergenceKind.HIDDEN_POSITIVE,
            }
            volume_confirmed = _volume_confirmation(
                frame,
                first.position,
                second.position,
                positive=positive,
            )
            price_change = ((second.price / first.price) - 1.0) * 100.0
            oscillator_change = second.oscillator - first.oscillator
            confidence_score, confidence_level = _confidence(
                price_change_percent=price_change,
                oscillator_change=oscillator_change,
                bar_distance=distance,
                volume_confirmation=volume_confirmed,
                oscillator=oscillator_column,
            )

            explanation = (
                f"Fiyat %{price_change:+.2f}, "
                f"{oscillator_column} {oscillator_change:+.2f} değişti; "
                f"pivot mesafesi {distance} bar."
            )
            signals.append(
                DivergenceSignal(
                    timeframe=timeframe,
                    oscillator=(
                        "RSI"
                        if oscillator_column == "RSI14"
                        else "MACD Histogram"
                    ),
                    kind=kind,
                    first=first,
                    second=second,
                    price_change_percent=round(price_change, 2),
                    oscillator_change=round(oscillator_change, 4),
                    volume_confirmation=volume_confirmed,
                    confidence_score=confidence_score,
                    confidence_level=confidence_level,
                    explanation=explanation,
                )
            )

    return tuple(
        sorted(
            signals,
            key=lambda signal: (
                signal.second.timestamp,
                signal.confidence_score,
            ),
            reverse=True,
        )
    )


def analyze_divergences(
    frame: pd.DataFrame,
    *,
    timeframe: str,
    left_bars: int = 3,
    right_bars: int = 3,
    minimum_bar_distance: int = 5,
    maximum_bar_distance: int = 40,
    minimum_price_change_percent: float = 1.0,
    minimum_rsi_change: float = 3.0,
    minimum_macd_change: float = 0.03,
    recent_bar_limit: int = 25,
) -> TimeframeDivergenceResult:
    _validate_frame(frame)

    if left_bars < 1 or right_bars < 1:
        raise DivergenceAnalysisError("Pivot sağ/sol bar sayısı en az 1 olmalıdır.")
    if minimum_bar_distance < 2:
        raise DivergenceAnalysisError("Minimum pivot mesafesi en az 2 bardır.")
    if maximum_bar_distance <= minimum_bar_distance:
        raise DivergenceAnalysisError(
            "Maksimum pivot mesafesi minimum mesafeden büyük olmalıdır."
        )
    if minimum_price_change_percent <= 0:
        raise DivergenceAnalysisError(
            "Minimum fiyat farkı sıfırdan büyük olmalıdır."
        )

    indicators = teknik_gostergeleri_ekle(frame.copy())
    usable = indicators.dropna(
        subset=["Close", "Volume", "RSI14", "MACD_Histogram"]
    )
    if len(usable) < 30:
        raise DivergenceAnalysisError(
            "Göstergeler sonrasında yeterli uyumsuzluk verisi kalmadı."
        )

    rsi_signals = _signals_for_oscillator(
        usable,
        timeframe=timeframe,
        oscillator_column="RSI14",
        left_bars=left_bars,
        right_bars=right_bars,
        minimum_bar_distance=minimum_bar_distance,
        maximum_bar_distance=maximum_bar_distance,
        minimum_price_change_percent=minimum_price_change_percent,
        minimum_oscillator_change=minimum_rsi_change,
        recent_bar_limit=recent_bar_limit,
    )
    macd_signals = _signals_for_oscillator(
        usable,
        timeframe=timeframe,
        oscillator_column="MACD_Histogram",
        left_bars=left_bars,
        right_bars=right_bars,
        minimum_bar_distance=minimum_bar_distance,
        maximum_bar_distance=maximum_bar_distance,
        minimum_price_change_percent=minimum_price_change_percent,
        minimum_oscillator_change=minimum_macd_change,
        recent_bar_limit=recent_bar_limit,
    )

    signals = tuple(
        sorted(
            rsi_signals + macd_signals,
            key=lambda signal: (
                signal.second.timestamp,
                signal.confidence_score,
            ),
            reverse=True,
        )
    )

    positive_count = sum(
        signal.kind in {
            DivergenceKind.NORMAL_POSITIVE,
            DivergenceKind.HIDDEN_POSITIVE,
        }
        for signal in signals
    )
    negative_count = len(signals) - positive_count

    if not signals:
        summary = "Son dönemde belirgin ve teyitli RSI/MACD uyumsuzluğu yok."
    elif positive_count and not negative_count:
        summary = "Pozitif yönlü uyumsuzluklar öne çıkıyor."
    elif negative_count and not positive_count:
        summary = "Negatif yönlü uyumsuzluklar öne çıkıyor."
    else:
        summary = "Pozitif ve negatif uyumsuzluklar birlikte görülüyor."

    return TimeframeDivergenceResult(
        timeframe=timeframe,
        latest_timestamp=pd.Timestamp(usable.index[-1]),
        signals=signals,
        summary=summary,
        positive_count=positive_count,
        negative_count=negative_count,
    )


def analyze_daily_weekly_divergences(
    daily_frame: pd.DataFrame,
    weekly_frame: pd.DataFrame,
) -> tuple[TimeframeDivergenceResult, TimeframeDivergenceResult]:
    daily = analyze_divergences(
        daily_frame,
        timeframe="Günlük",
        minimum_price_change_percent=1.0,
        recent_bar_limit=25,
    )
    weekly = analyze_divergences(
        weekly_frame,
        timeframe="Haftalık",
        minimum_price_change_percent=2.0,
        minimum_rsi_change=4.0,
        minimum_macd_change=0.05,
        recent_bar_limit=16,
    )
    return daily, weekly


def divergence_rows(
    results: Iterable[TimeframeDivergenceResult],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in results:
        for signal in result.signals:
            rows.append(
                {
                    "Zaman dilimi": result.timeframe,
                    "Gösterge": signal.oscillator,
                    "Uyumsuzluk": signal.kind.value,
                    "İlk pivot": signal.first.timestamp,
                    "İkinci pivot": signal.second.timestamp,
                    "Fiyat değişimi (%)": signal.price_change_percent,
                    "Osilatör değişimi": signal.oscillator_change,
                    "Hacim teyidi": (
                        "Var" if signal.volume_confirmation else "Yok"
                    ),
                    "Güven": signal.confidence_level,
                    "Güven skoru": signal.confidence_score,
                }
            )
    return rows
