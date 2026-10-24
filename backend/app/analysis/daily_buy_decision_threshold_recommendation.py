from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .daily_buy_decision_calibration import CalibrationSlice, MIN_SAMPLE


@dataclass(frozen=True)
class ThresholdRecommendation:
    dimension: str
    horizon: str
    recommendation: str
    preferred_segment: str | None
    review_segment: str | None
    evidence: str
    sample_size: int


def _eligible(items: Iterable[CalibrationSlice]) -> tuple[CalibrationSlice, ...]:
    return tuple(
        item
        for item in items
        if item.sample_size >= MIN_SAMPLE
        and item.hit_rate is not None
        and item.average_return is not None
    )


def build_threshold_recommendations(
    slices: Iterable[CalibrationSlice],
) -> tuple[ThresholdRecommendation, ...]:
    """Read-only threshold evidence; never mutates decision thresholds."""

    grouped: dict[tuple[str, str], list[CalibrationSlice]] = defaultdict(list)
    for item in slices:
        grouped[(item.dimension, item.horizon)].append(item)

    result: list[ThresholdRecommendation] = []
    for (dimension, horizon), items in sorted(grouped.items()):
        eligible = _eligible(items)
        if not eligible:
            sample = max((item.sample_size for item in items), default=0)
            result.append(
                ThresholdRecommendation(
                    dimension=dimension,
                    horizon=horizon,
                    recommendation="YETERSİZ VERİ",
                    preferred_segment=None,
                    review_segment=None,
                    evidence=f"En büyük segment örneği {sample}; minimum {MIN_SAMPLE} gerekli.",
                    sample_size=sample,
                )
            )
            continue

        best = max(
            eligible,
            key=lambda item: (float(item.hit_rate), float(item.average_return), item.sample_size),
        )
        worst = min(
            eligible,
            key=lambda item: (float(item.hit_rate), float(item.average_return), -item.sample_size),
        )

        supportive = [item for item in eligible if item.status == "DESTEKLEYİCİ"]
        review = [item for item in eligible if item.status == "GÖZDEN GEÇİR"]

        if supportive and review:
            recommendation = "EŞİK İNCELEME ADAYI"
            evidence = (
                f"{best.segment}: isabet %{best.hit_rate:.1f}, ort. getiri %{best.average_return:.2f}; "
                f"{worst.segment}: isabet %{worst.hit_rate:.1f}, ort. getiri %{worst.average_return:.2f}. "
                "Yalnız manuel inceleme önerilir; otomatik eşik değişikliği yapılmaz."
            )
            preferred = best.segment
            review_segment = worst.segment
        elif supportive:
            recommendation = "MEVCUT EŞİĞİ KORU"
            evidence = (
                f"En güçlü segment {best.segment}: isabet %{best.hit_rate:.1f}, "
                f"ort. getiri %{best.average_return:.2f}. Otomatik değişiklik yok."
            )
            preferred = best.segment
            review_segment = None
        elif review:
            recommendation = "MANUEL GÖZDEN GEÇİR"
            evidence = (
                f"En zayıf segment {worst.segment}: isabet %{worst.hit_rate:.1f}, "
                f"ort. getiri %{worst.average_return:.2f}. Eşik değişikliği insan onayı gerektirir."
            )
            preferred = None
            review_segment = worst.segment
        else:
            recommendation = "İZLE"
            evidence = (
                f"Yeterli örnek var ancak belirgin destekleyici/zayıf ayrışma yok. "
                f"En güçlü segment {best.segment}: isabet %{best.hit_rate:.1f}, "
                f"ort. getiri %{best.average_return:.2f}."
            )
            preferred = best.segment
            review_segment = None

        result.append(
            ThresholdRecommendation(
                dimension=dimension,
                horizon=horizon,
                recommendation=recommendation,
                preferred_segment=preferred,
                review_segment=review_segment,
                evidence=evidence,
                sample_size=max(item.sample_size for item in eligible),
            )
        )

    return tuple(result)


def threshold_recommendation_rows(
    recommendations: Iterable[ThresholdRecommendation],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Boyut": item.dimension,
            "Ufuk": item.horizon,
            "Öneri": item.recommendation,
            "Desteklenen segment": item.preferred_segment or "-",
            "İncelenecek segment": item.review_segment or "-",
            "Örnek": item.sample_size,
            "Kanıt": item.evidence,
        }
        for item in recommendations
    )
