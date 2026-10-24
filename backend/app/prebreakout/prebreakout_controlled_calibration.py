from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RegimeCalibrationSample:
    regime: str
    sample_count: int
    successful_count: int

    @property
    def success_rate_pct(self) -> float | None:
        if self.sample_count <= 0:
            return None
        return round(self.successful_count * 100.0 / self.sample_count, 4)


@dataclass(frozen=True)
class ThresholdCalibrationScenario:
    name: str
    momentum_min: float
    require_positive_rsi_slope: bool
    require_positive_macd_histogram_slope: bool
    sample_count: int
    successful_count: int
    false_positive_count: int
    missed_opportunity_count: int
    regimes: tuple[RegimeCalibrationSample, ...] = ()

    @property
    def success_rate_pct(self) -> float | None:
        if self.sample_count <= 0:
            return None
        return round(self.successful_count * 100.0 / self.sample_count, 4)

    @property
    def false_positive_rate_pct(self) -> float | None:
        if self.sample_count <= 0:
            return None
        return round(self.false_positive_count * 100.0 / self.sample_count, 4)


@dataclass(frozen=True)
class CalibrationEvaluationRow:
    name: str
    success_rate_pct: float | None
    success_improvement_pp: float | None
    false_positive_rate_pct: float | None
    false_positive_change_pp: float | None
    sample_retention_pct: float | None
    reliable_regime_count: int
    worst_reliable_regime_success_pct: float | None
    eligible: bool
    rejection_reasons: tuple[str, ...]
    score: float | None


@dataclass(frozen=True)
class ControlledCalibrationReport:
    baseline_name: str
    evaluated_candidate_count: int
    rows: tuple[CalibrationEvaluationRow, ...]
    recommended_scenario_name: str | None
    keep_baseline: bool
    automatic_apply_allowed: bool
    note: str


def _validate_scenario(item: ThresholdCalibrationScenario) -> None:
    if item.sample_count < 0 or item.successful_count < 0 or item.false_positive_count < 0:
        raise ValueError("Senaryo sayımları negatif olamaz.")
    if item.successful_count > item.sample_count:
        raise ValueError("Başarılı sayısı örneklemden büyük olamaz.")
    if item.false_positive_count > item.sample_count:
        raise ValueError("Yanlış pozitif sayısı örneklemden büyük olamaz.")
    if item.missed_opportunity_count < 0:
        raise ValueError("Kaçırılan fırsat sayısı negatif olamaz.")
    for regime in item.regimes:
        if regime.sample_count < 0 or regime.successful_count < 0 or regime.successful_count > regime.sample_count:
            raise ValueError("Rejim örneklem sayımları geçersiz.")


def _reliable_regime_rates(
    item: ThresholdCalibrationScenario,
    minimum_regime_sample: int,
) -> tuple[float, ...]:
    values: list[float] = []
    for regime in item.regimes:
        if regime.sample_count >= minimum_regime_sample and regime.success_rate_pct is not None:
            values.append(float(regime.success_rate_pct))
    return tuple(values)


def kontrollu_esik_kalibrasyonunu_degerlendir(
    baseline: ThresholdCalibrationScenario,
    candidates: Iterable[ThresholdCalibrationScenario],
    *,
    minimum_total_sample: int = 30,
    minimum_regime_sample: int = 8,
    minimum_reliable_regime_count: int = 2,
    minimum_sample_retention_pct: float = 70.0,
    minimum_success_improvement_pp: float = 2.0,
    maximum_false_positive_increase_pp: float = 0.0,
    maximum_worst_regime_degradation_pp: float = 3.0,
) -> ControlledCalibrationReport:
    """Tarihsel eşik adaylarını aşırı uyum riskine karşı temkinli değerlendirir.

    Bu fonksiyon üretim eşiklerini değiştirmez. Yalnızca yeterli örneklem, rejim
    dengesi, örneklem korunumu ve yanlış-pozitif etkisini birlikte değerlendirerek
    bir aday önerisi üretir. Uygulama kararı ayrı bir kontrollü sprintte verilmelidir.
    """
    if minimum_total_sample < 1:
        raise ValueError("Minimum toplam örneklem en az 1 olmalıdır.")
    if minimum_regime_sample < 1:
        raise ValueError("Minimum rejim örneklemi en az 1 olmalıdır.")
    if minimum_reliable_regime_count < 1:
        raise ValueError("Minimum güvenilir rejim sayısı en az 1 olmalıdır.")
    if not 0.0 < minimum_sample_retention_pct <= 100.0:
        raise ValueError("Örneklem koruma eşiği 0-100 aralığında olmalıdır.")
    if minimum_success_improvement_pp < 0.0:
        raise ValueError("Başarı iyileşme eşiği negatif olamaz.")
    if maximum_false_positive_increase_pp < 0.0 or maximum_worst_regime_degradation_pp < 0.0:
        raise ValueError("Toleranslar negatif olamaz.")

    _validate_scenario(baseline)
    baseline_success = baseline.success_rate_pct
    baseline_fp = baseline.false_positive_rate_pct
    if baseline.sample_count < 1 or baseline_success is None or baseline_fp is None:
        raise ValueError("Temel senaryonun ölçülebilir örneklemi olmalıdır.")

    baseline_regime_rates = _reliable_regime_rates(baseline, minimum_regime_sample)
    baseline_worst_regime = min(baseline_regime_rates) if baseline_regime_rates else None

    rows: list[CalibrationEvaluationRow] = []
    for candidate in tuple(candidates):
        _validate_scenario(candidate)
        success_rate = candidate.success_rate_pct
        fp_rate = candidate.false_positive_rate_pct
        retention = round(candidate.sample_count * 100.0 / baseline.sample_count, 4)
        success_delta = None if success_rate is None else round(success_rate - baseline_success, 4)
        fp_delta = None if fp_rate is None else round(fp_rate - baseline_fp, 4)
        reliable_rates = _reliable_regime_rates(candidate, minimum_regime_sample)
        worst_regime = min(reliable_rates) if reliable_rates else None

        reasons: list[str] = []
        if candidate.sample_count < minimum_total_sample:
            reasons.append("Toplam örneklem yetersiz")
        if retention < minimum_sample_retention_pct:
            reasons.append("Örneklem kaybı fazla")
        if len(reliable_rates) < minimum_reliable_regime_count:
            reasons.append("Rejim çeşitliliği yetersiz")
        if success_delta is None or success_delta < minimum_success_improvement_pp:
            reasons.append("Başarı artışı yetersiz")
        if fp_delta is None or fp_delta > maximum_false_positive_increase_pp:
            reasons.append("Yanlış pozitif oranı kötüleşiyor")
        if baseline_worst_regime is not None:
            if worst_regime is None:
                reasons.append("En zayıf rejim karşılaştırılamıyor")
            elif worst_regime < baseline_worst_regime - maximum_worst_regime_degradation_pp:
                reasons.append("En zayıf rejimde bozulma fazla")

        eligible = not reasons
        score: float | None = None
        if eligible and success_delta is not None and fp_delta is not None:
            retention_loss = max(0.0, 100.0 - retention)
            missed_penalty = max(0, candidate.missed_opportunity_count - baseline.missed_opportunity_count)
            score = round(success_delta - 0.50 * fp_delta - 0.05 * retention_loss - 0.10 * missed_penalty, 4)

        rows.append(
            CalibrationEvaluationRow(
                name=candidate.name,
                success_rate_pct=success_rate,
                success_improvement_pp=success_delta,
                false_positive_rate_pct=fp_rate,
                false_positive_change_pp=fp_delta,
                sample_retention_pct=retention,
                reliable_regime_count=len(reliable_rates),
                worst_reliable_regime_success_pct=worst_regime,
                eligible=eligible,
                rejection_reasons=tuple(reasons),
                score=score,
            )
        )

    eligible_rows = [row for row in rows if row.eligible and row.score is not None]
    eligible_rows.sort(key=lambda row: (row.score, row.success_improvement_pp or -9999.0, row.sample_retention_pct or 0.0), reverse=True)
    recommended = eligible_rows[0].name if eligible_rows else None
    keep_baseline = recommended is None
    note = (
        "Hiçbir aday aşırı uyum ve örneklem güvenlik kapılarını geçmedi; mevcut eşikler korunmalı."
        if keep_baseline
        else f"Kontrollü kalibrasyon adayı: {recommended}. Bu yalnız öneridir; üretim eşikleri otomatik uygulanmaz."
    )

    return ControlledCalibrationReport(
        baseline_name=baseline.name,
        evaluated_candidate_count=len(rows),
        rows=tuple(rows),
        recommended_scenario_name=recommended,
        keep_baseline=keep_baseline,
        automatic_apply_allowed=False,
        note=note,
    )


def kalibrasyon_degerlendirme_tablosu(report: ControlledCalibrationReport) -> list[dict[str, object]]:
    return [
        {
            "Senaryo": row.name,
            "Başarı oranı (%)": row.success_rate_pct,
            "Başarı farkı (puan)": row.success_improvement_pp,
            "Yanlış pozitif (%)": row.false_positive_rate_pct,
            "Yanlış pozitif farkı (puan)": row.false_positive_change_pp,
            "Örneklem korunumu (%)": row.sample_retention_pct,
            "Güvenilir rejim": row.reliable_regime_count,
            "En zayıf rejim başarı (%)": row.worst_reliable_regime_success_pct,
            "Uygun aday": row.eligible,
            "Red nedenleri": "; ".join(row.rejection_reasons),
            "Kalibrasyon skoru": row.score,
        }
        for row in report.rows
    ]
