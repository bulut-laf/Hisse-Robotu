from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from .signal_outcome_tracking import SignalOutcome
from .shadow_portfolio import ShadowPosition
from .success_comparison_report import SuccessComparisonReport
from ..data.delayed_data_pilot import PilotLogRecord


DEVAM = "Devam"
TEMKINLI_DEVAM = "Temkinli Devam"
KALIBRASYON_GEREKLI = "Kalibrasyon Gerekli"


@dataclass(frozen=True)
class CalibrationCriterion:
    name: str
    status: str
    detail: str
    critical: bool


@dataclass(frozen=True)
class V13CalibrationDecision:
    decision: str
    generated_at: str
    criteria: tuple[CalibrationCriterion, ...]
    pilot_measurement_count: int
    signal_record_count: int
    completed_horizon_count: int
    pending_horizon_count: int
    shadow_position_count: int
    closed_shadow_position_count: int
    comparison_row_count: int
    sufficient_comparison_count: int
    insufficient_comparison_count: int

    @property
    def failed_critical_count(self) -> int:
        return sum(
            item.critical and item.status == "Başarısız"
            for item in self.criteria
        )

    @property
    def warning_count(self) -> int:
        return sum(item.status == "Uyarı" for item in self.criteria)


def _criterion(
    name: str,
    *,
    passed: bool,
    detail: str,
    critical: bool,
    warning_when_failed: bool = False,
) -> CalibrationCriterion:
    if passed:
        status = "Başarılı"
    elif warning_when_failed:
        status = "Uyarı"
    else:
        status = "Başarısız"
    return CalibrationCriterion(
        name=name,
        status=status,
        detail=detail,
        critical=critical,
    )


def build_v13_calibration_decision(
    *,
    pilot_records: Iterable[PilotLogRecord],
    signal_outcomes: Iterable[SignalOutcome],
    shadow_positions: Iterable[ShadowPosition],
    comparison_report: SuccessComparisonReport,
    minimum_pilot_measurements: int = 5,
    minimum_completed_horizons: int = 15,
    minimum_closed_positions: int = 5,
    minimum_sufficient_comparisons: int = 3,
) -> V13CalibrationDecision:
    pilots = tuple(pilot_records)
    outcomes = tuple(signal_outcomes)
    positions = tuple(shadow_positions)

    completed_horizons = sum(
        horizon.available
        for outcome in outcomes
        for horizon in outcome.horizons
    )
    pending_horizons = sum(
        not horizon.available
        for outcome in outcomes
        for horizon in outcome.horizons
    )
    closed_positions = sum(
        item.status == "Kapalı"
        for item in positions
    )
    sufficient = sum(
        item.sample_status == "Yeterli"
        for item in comparison_report.rows
    )
    insufficient = len(comparison_report.rows) - sufficient
    unlocked_pilots = sum(not item.locked for item in pilots)

    criteria = (
        _criterion(
            "Gecikmeli veri pilotu",
            passed=(
                len(pilots) >= minimum_pilot_measurements
                and unlocked_pilots > 0
            ),
            detail=(
                f"{len(pilots)} ölçüm · {unlocked_pilots} kilitsiz ölçüm · "
                f"hedef en az {minimum_pilot_measurements}"
            ),
            critical=True,
        ),
        _criterion(
            "Otomatik sinyal sonuç zinciri",
            passed=completed_horizons >= minimum_completed_horizons,
            detail=(
                f"{len(outcomes)} sinyal · {completed_horizons} tamamlanan · "
                f"{pending_horizons} bekleyen ufuk · hedef en az "
                f"{minimum_completed_horizons} tamamlanan ufuk"
            ),
            critical=True,
        ),
        _criterion(
            "Gölge portföy örneklemi",
            passed=closed_positions >= minimum_closed_positions,
            detail=(
                f"{len(positions)} toplam · {closed_positions} kapalı pozisyon · "
                f"hedef en az {minimum_closed_positions}"
            ),
            critical=False,
            warning_when_failed=True,
        ),
        _criterion(
            "Rejim/sektör/gösterge karşılaştırması",
            passed=sufficient >= minimum_sufficient_comparisons,
            detail=(
                f"{sufficient} yeterli · {insufficient} yetersiz örneklem satırı · "
                f"hedef en az {minimum_sufficient_comparisons} yeterli grup"
            ),
            critical=False,
            warning_when_failed=True,
        ),
        _criterion(
            "V1.3 veri bütünlüğü",
            passed=bool(comparison_report.rows or outcomes or positions or pilots),
            detail=(
                "Sprint-75–80 kayıt zincirlerinden en az biri okunabildi."
                if (comparison_report.rows or outcomes or positions or pilots)
                else "Sprint-75–80 kayıt zincirlerinde veri bulunamadı."
            ),
            critical=True,
        ),
    )

    failed_critical = sum(
        item.critical and item.status == "Başarısız"
        for item in criteria
    )
    warnings = sum(item.status == "Uyarı" for item in criteria)

    if failed_critical:
        decision = KALIBRASYON_GEREKLI
    elif warnings:
        decision = TEMKINLI_DEVAM
    else:
        decision = DEVAM

    return V13CalibrationDecision(
        decision=decision,
        generated_at=datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        criteria=criteria,
        pilot_measurement_count=len(pilots),
        signal_record_count=len(outcomes),
        completed_horizon_count=completed_horizons,
        pending_horizon_count=pending_horizons,
        shadow_position_count=len(positions),
        closed_shadow_position_count=closed_positions,
        comparison_row_count=len(comparison_report.rows),
        sufficient_comparison_count=sufficient,
        insufficient_comparison_count=insufficient,
    )


def criterion_rows(
    decision: V13CalibrationDecision,
) -> list[dict[str, object]]:
    return [
        {
            "Kriter": item.name,
            "Durum": item.status,
            "Kritik": "Evet" if item.critical else "Hayır",
            "Açıklama": item.detail,
        }
        for item in decision.criteria
    ]


def decision_summary_rows(
    decision: V13CalibrationDecision,
) -> list[dict[str, object]]:
    return [
        {"Metrik": "Kalibrasyon kararı", "Değer": decision.decision},
        {
            "Metrik": "Pilot ölçümü",
            "Değer": decision.pilot_measurement_count,
        },
        {
            "Metrik": "Sinyal kaydı",
            "Değer": decision.signal_record_count,
        },
        {
            "Metrik": "Tamamlanan 5/10/20 ufku",
            "Değer": decision.completed_horizon_count,
        },
        {
            "Metrik": "Bekleyen 5/10/20 ufku",
            "Değer": decision.pending_horizon_count,
        },
        {
            "Metrik": "Gölge pozisyon",
            "Değer": decision.shadow_position_count,
        },
        {
            "Metrik": "Kapalı gölge pozisyon",
            "Değer": decision.closed_shadow_position_count,
        },
        {
            "Metrik": "Yeterli karşılaştırma",
            "Değer": decision.sufficient_comparison_count,
        },
        {
            "Metrik": "Yetersiz karşılaştırma",
            "Değer": decision.insufficient_comparison_count,
        },
    ]
