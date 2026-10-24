from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd


EVALUATED_LABELS = frozenset(
    {"Başarılı", "Sınırlı hareket", "Yanlış pozitif"}
)


@dataclass(frozen=True)
class ThresholdCalibrationConfig:
    current_threshold: int = 45
    alternative_thresholds: tuple[int, ...] = (35, 40, 50, 55)
    minimum_sample_size: int = 10
    minimum_coverage_pct: float = 60.0
    minimum_quality_gain: float = 3.0

    def __post_init__(self) -> None:
        thresholds = (self.current_threshold, *self.alternative_thresholds)
        if any(not 0 <= value <= 100 for value in thresholds):
            raise ValueError("Eşikler 0 ile 100 arasında olmalıdır.")
        if self.minimum_sample_size < 1:
            raise ValueError("Minimum örneklem en az 1 olmalıdır.")
        if not 0.0 <= self.minimum_coverage_pct <= 100.0:
            raise ValueError("Minimum kapsama 0 ile 100 arasında olmalıdır.")
        if self.minimum_quality_gain < 0.0:
            raise ValueError("Minimum kalite kazanımı negatif olamaz.")


@dataclass(frozen=True)
class ThresholdCalibrationRecommendation:
    current_threshold: int
    recommended_threshold: int
    decision: str
    reason: str
    automatic_change_applied: bool = False


@dataclass(frozen=True)
class ThresholdCalibrationReport:
    comparison: pd.DataFrame
    recommendation: ThresholdCalibrationRecommendation


def calibration_thresholds(
    config: ThresholdCalibrationConfig,
) -> tuple[int, ...]:
    return tuple(
        sorted(set((config.current_threshold, *config.alternative_thresholds)))
    )


def _rate(count: int, total: int) -> float:
    return count / total * 100.0 if total else 0.0


def _empty_comparison() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "threshold",
            "is_current",
            "sample_count",
            "evaluated_count",
            "successful",
            "limited_move",
            "false_positive",
            "success_rate_pct",
            "false_positive_rate_pct",
            "coverage_vs_current_pct",
            "quality_score",
            "sample_sufficient",
        ]
    )


def compare_thresholds(
    records_table: pd.DataFrame,
    config: ThresholdCalibrationConfig,
) -> pd.DataFrame:
    required = {"score", "performance_label"}
    missing = required.difference(records_table.columns)
    if missing and not records_table.empty:
        raise ValueError(
            "Kalibrasyon tablosunda eksik sütunlar: "
            + ", ".join(sorted(missing))
        )
    if records_table.empty:
        return _empty_comparison()

    table = records_table.copy()
    table["score"] = pd.to_numeric(table["score"], errors="coerce")
    table = table.dropna(subset=["score"])

    current_count = int(
        (table["score"] >= config.current_threshold).sum()
    )
    rows: list[dict[str, object]] = []

    for threshold in calibration_thresholds(config):
        selected = table[table["score"] >= threshold]
        evaluated = selected[
            selected["performance_label"].isin(EVALUATED_LABELS)
        ]
        successful = int(
            (evaluated["performance_label"] == "Başarılı").sum()
        )
        limited = int(
            (evaluated["performance_label"] == "Sınırlı hareket").sum()
        )
        false_positive = int(
            (evaluated["performance_label"] == "Yanlış pozitif").sum()
        )
        evaluated_count = len(evaluated)
        success_rate = _rate(successful, evaluated_count)
        false_positive_rate = _rate(false_positive, evaluated_count)
        coverage = _rate(len(selected), current_count) if current_count else 0.0

        rows.append(
            {
                "threshold": threshold,
                "is_current": threshold == config.current_threshold,
                "sample_count": len(selected),
                "evaluated_count": evaluated_count,
                "successful": successful,
                "limited_move": limited,
                "false_positive": false_positive,
                "success_rate_pct": round(success_rate, 2),
                "false_positive_rate_pct": round(false_positive_rate, 2),
                "coverage_vs_current_pct": round(coverage, 2),
                "quality_score": round(
                    success_rate - false_positive_rate,
                    2,
                ),
                "sample_sufficient": (
                    evaluated_count >= config.minimum_sample_size
                ),
            }
        )

    return pd.DataFrame(rows)


def recommend_threshold(
    comparison: pd.DataFrame,
    config: ThresholdCalibrationConfig,
) -> ThresholdCalibrationRecommendation:
    keep = ThresholdCalibrationRecommendation(
        current_threshold=config.current_threshold,
        recommended_threshold=config.current_threshold,
        decision="Mevcut eşiği koru",
        reason="Güvenilir bir alternatif üstünlüğü oluşmadı.",
    )
    if comparison.empty:
        return ThresholdCalibrationRecommendation(
            current_threshold=config.current_threshold,
            recommended_threshold=config.current_threshold,
            decision="Yetersiz veri",
            reason="Kalibrasyon karşılaştırması için kayıt bulunamadı.",
        )

    current_rows = comparison[comparison["is_current"]]
    if current_rows.empty:
        return keep
    current = current_rows.iloc[0]
    if not bool(current["sample_sufficient"]):
        return ThresholdCalibrationRecommendation(
            current_threshold=config.current_threshold,
            recommended_threshold=config.current_threshold,
            decision="Yetersiz örneklem",
            reason=(
                "Mevcut eşik için değerlendirilebilir örneklem minimum "
                "sınırın altında; eşik değişikliği önerilmedi."
            ),
        )

    candidates = comparison[
        (~comparison["is_current"])
        & comparison["sample_sufficient"]
        & (comparison["coverage_vs_current_pct"] >= config.minimum_coverage_pct)
        & (comparison["success_rate_pct"] >= current["success_rate_pct"])
        & (
            comparison["false_positive_rate_pct"]
            <= current["false_positive_rate_pct"]
        )
        & (
            comparison["quality_score"]
            >= current["quality_score"] + config.minimum_quality_gain
        )
    ]
    if candidates.empty:
        return keep

    best = candidates.sort_values(
        by=[
            "quality_score",
            "coverage_vs_current_pct",
            "sample_count",
            "threshold",
        ],
        ascending=[False, False, False, False],
    ).iloc[0]
    threshold = int(best["threshold"])
    return ThresholdCalibrationRecommendation(
        current_threshold=config.current_threshold,
        recommended_threshold=threshold,
        decision="İnceleme için alternatif eşik önerisi",
        reason=(
            f"{threshold} eşiği, yeterli örneklem ve kapsama korunurken "
            "başarı/yanlış-pozitif dengesini iyileştirdi. Üretim eşiği "
            "otomatik değiştirilmedi."
        ),
    )


def generate_calibration_report(
    records_table: pd.DataFrame,
    config: ThresholdCalibrationConfig,
) -> ThresholdCalibrationReport:
    comparison = compare_thresholds(records_table, config)
    return ThresholdCalibrationReport(
        comparison=comparison,
        recommendation=recommend_threshold(comparison, config),
    )


def filter_records_for_threshold(
    records: Sequence[object],
    threshold: int,
) -> tuple[object, ...]:
    if not 0 <= threshold <= 100:
        raise ValueError("Eşik 0 ile 100 arasında olmalıdır.")
    return tuple(
        record
        for record in records
        if getattr(getattr(record, "replay").analysis, "score") >= threshold
    )
