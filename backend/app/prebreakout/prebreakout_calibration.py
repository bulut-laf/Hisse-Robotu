from __future__ import annotations

from dataclasses import dataclass, replace
from math import sqrt
from typing import Iterable, Sequence

import pandas as pd

from backend.app.prebreakout.prebreakout_backtest import (
    PreBreakoutPerformanceLabel,
    PreBreakoutReplayResult,
    performans_etiketi_belirle,
)
from backend.app.prebreakout.prebreakout_threshold_policy import (
    PreBreakoutThresholdPolicy,
)


@dataclass(frozen=True)
class PreBreakoutCalibrationRow:
    stage: str
    candidate_count: int
    measured_count: int
    successful_count: int
    limited_count: int
    false_positive_count: int
    success_rate_pct: float
    average_close_return_5d_pct: float | None
    average_close_return_10d_pct: float | None
    average_close_return_20d_pct: float | None
    average_max_return_5d_pct: float | None
    average_max_return_10d_pct: float | None
    average_max_return_20d_pct: float | None
    average_min_return_5d_pct: float | None
    average_min_return_10d_pct: float | None
    average_min_return_20d_pct: float | None


@dataclass(frozen=True)
class PreBreakoutMomentumCalibrationRow:
    stage: str
    momentum_band: str
    candidate_count: int
    measured_count: int
    successful_count: int
    success_rate_pct: float
    average_macd_histogram_slope: float | None
    average_rsi_slope: float | None


@dataclass(frozen=True)
class PreBreakoutCalibrationSummary:
    candidate_count: int
    measured_count: int
    measurement_coverage_pct: float
    reliable_stage_count: int
    best_stage: str | None
    best_stage_success_rate_pct: float
    sufficient_sample: bool
    note: str


@dataclass(frozen=True)
class PreBreakoutStageConfidenceRow:
    stage: str
    measured_count: int
    successful_count: int
    success_rate_pct: float
    confidence_low_pct: float
    confidence_high_pct: float
    sample_sufficient: bool
    conservative_rank: int | None


@dataclass(frozen=True)
class PreBreakoutLeaderSensitivityRow:
    stage: str
    removed_outcome: str
    scenario_leader: str | None
    baseline_leader_retained: bool


@dataclass(frozen=True)
class PreBreakoutLeaderStabilitySummary:
    baseline_leader: str | None
    scenario_count: int
    retained_count: int
    retention_rate_pct: float
    stable: bool
    note: str


@dataclass(frozen=True)
class PreBreakoutThresholdRecommendation:
    stage: str
    recommended_action: str
    recommended_minimum_momentum_score: int | None
    evidence_level: str
    confidence_low_pct: float
    measured_count: int
    leader_stable: bool
    auto_apply: bool
    rationale: str


@dataclass(frozen=True)
class PreBreakoutThresholdValidationRow:
    stage: str
    current_minimum_momentum_score: int
    proposed_minimum_momentum_score: int
    baseline_measured_count: int
    baseline_success_rate_pct: float
    candidate_measured_count: int
    candidate_success_rate_pct: float
    success_rate_delta_pct: float
    candidate_confidence_low_pct: float
    sample_retention_pct: float
    verdict: str
    auto_apply: bool


def _rate(part: int, total: int) -> float:
    return round(part / total * 100.0, 2) if total else 0.0


def _average(values: Iterable[float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(sum(clean) / len(clean), 4) if clean else None


def _performance(result: PreBreakoutReplayResult, horizon: int, field: str):
    for item in result.forward:
        if item.horizon == horizon and item.available:
            return getattr(item, field)
    return None


def _measured_label(result: PreBreakoutReplayResult) -> str:
    return performans_etiketi_belirle(result)


def _is_measured(label: str) -> bool:
    return label in {
        PreBreakoutPerformanceLabel.BASARILI,
        PreBreakoutPerformanceLabel.SINIRLI_HAREKET,
        PreBreakoutPerformanceLabel.YANLIS_POZITIF,
    }


def asama_kalibrasyonunu_hesapla(
    results: Sequence[PreBreakoutReplayResult],
) -> tuple[PreBreakoutCalibrationRow, ...]:
    rows: list[PreBreakoutCalibrationRow] = []
    stages = sorted({result.analysis.stage.value for result in results})
    for stage in stages:
        candidates = [r for r in results if r.analysis.stage.value == stage]
        labeled = [(r, _measured_label(r)) for r in candidates]
        measured = [(r, label) for r, label in labeled if _is_measured(label)]
        successful = sum(
            label == PreBreakoutPerformanceLabel.BASARILI
            for _, label in measured
        )
        limited = sum(
            label == PreBreakoutPerformanceLabel.SINIRLI_HAREKET
            for _, label in measured
        )
        false_positive = sum(
            label == PreBreakoutPerformanceLabel.YANLIS_POZITIF
            for _, label in measured
        )
        metrics = {
            (kind, horizon): _average(
                _performance(result, horizon, kind)
                for result, _ in measured
            )
            for kind in ("close_return_pct", "max_return_pct", "min_return_pct")
            for horizon in (5, 10, 20)
        }
        rows.append(
            PreBreakoutCalibrationRow(
                stage=stage,
                candidate_count=len(candidates),
                measured_count=len(measured),
                successful_count=successful,
                limited_count=limited,
                false_positive_count=false_positive,
                success_rate_pct=_rate(successful, len(measured)),
                average_close_return_5d_pct=metrics[("close_return_pct", 5)],
                average_close_return_10d_pct=metrics[("close_return_pct", 10)],
                average_close_return_20d_pct=metrics[("close_return_pct", 20)],
                average_max_return_5d_pct=metrics[("max_return_pct", 5)],
                average_max_return_10d_pct=metrics[("max_return_pct", 10)],
                average_max_return_20d_pct=metrics[("max_return_pct", 20)],
                average_min_return_5d_pct=metrics[("min_return_pct", 5)],
                average_min_return_10d_pct=metrics[("min_return_pct", 10)],
                average_min_return_20d_pct=metrics[("min_return_pct", 20)],
            )
        )
    return tuple(rows)


def asama_kalibrasyonunu_tabloya_cevir(
    rows: Sequence[PreBreakoutCalibrationRow],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Aşama": row.stage,
                "Aday": row.candidate_count,
                "Ölçülen": row.measured_count,
                "Başarılı": row.successful_count,
                "Sınırlı hareket": row.limited_count,
                "Yanlış pozitif": row.false_positive_count,
                "Başarı oranı %": row.success_rate_pct,
                "5G kapanış ort. %": row.average_close_return_5d_pct,
                "10G kapanış ort. %": row.average_close_return_10d_pct,
                "20G kapanış ort. %": row.average_close_return_20d_pct,
                "5G en yüksek ort. %": row.average_max_return_5d_pct,
                "10G en yüksek ort. %": row.average_max_return_10d_pct,
                "20G en yüksek ort. %": row.average_max_return_20d_pct,
                "5G en düşük ort. %": row.average_min_return_5d_pct,
                "10G en düşük ort. %": row.average_min_return_10d_pct,
                "20G en düşük ort. %": row.average_min_return_20d_pct,
            }
            for row in rows
        ]
    )


def _momentum_band(score: int) -> str:
    if score < 10:
        return "0-9"
    if score < 15:
        return "10-14"
    return "15-20"


def momentum_kalibrasyonunu_hesapla(
    results: Sequence[PreBreakoutReplayResult],
) -> tuple[PreBreakoutMomentumCalibrationRow, ...]:
    groups: dict[tuple[str, str], list[PreBreakoutReplayResult]] = {}
    for result in results:
        components = result.analysis.component_scores
        if components is None:
            continue
        key = (result.analysis.stage.value, _momentum_band(components.momentum))
        groups.setdefault(key, []).append(result)

    rows: list[PreBreakoutMomentumCalibrationRow] = []
    for (stage, band), candidates in sorted(groups.items()):
        labeled = [(r, _measured_label(r)) for r in candidates]
        measured = [(r, label) for r, label in labeled if _is_measured(label)]
        successful = sum(
            label == PreBreakoutPerformanceLabel.BASARILI
            for _, label in measured
        )
        rows.append(
            PreBreakoutMomentumCalibrationRow(
                stage=stage,
                momentum_band=band,
                candidate_count=len(candidates),
                measured_count=len(measured),
                successful_count=successful,
                success_rate_pct=_rate(successful, len(measured)),
                average_macd_histogram_slope=_average(
                    r.analysis.features.macd_histogram_egimi
                    if r.analysis.features is not None else None
                    for r, _ in measured
                ),
                average_rsi_slope=_average(
                    r.analysis.features.rsi_egimi
                    if r.analysis.features is not None else None
                    for r, _ in measured
                ),
            )
        )
    return tuple(rows)


def momentum_kalibrasyonunu_tabloya_cevir(
    rows: Sequence[PreBreakoutMomentumCalibrationRow],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Aşama": row.stage,
                "Momentum bandı": row.momentum_band,
                "Aday": row.candidate_count,
                "Ölçülen": row.measured_count,
                "Başarılı": row.successful_count,
                "Başarı oranı %": row.success_rate_pct,
                "MACD histogram eğimi ort.": row.average_macd_histogram_slope,
                "RSI eğimi ort.": row.average_rsi_slope,
            }
            for row in rows
        ]
    )


def guvenilir_asama_satirlarini_sec(
    rows: Sequence[PreBreakoutCalibrationRow],
    *,
    minimum_sample_size: int = 3,
) -> tuple[PreBreakoutCalibrationRow, ...]:
    if minimum_sample_size < 1:
        raise ValueError("Minimum örneklem en az 1 olmalıdır.")
    return tuple(row for row in rows if row.measured_count >= minimum_sample_size)


def kalibrasyon_ozetini_hesapla(
    rows: Sequence[PreBreakoutCalibrationRow],
    *,
    minimum_sample_size: int = 3,
) -> PreBreakoutCalibrationSummary:
    reliable = guvenilir_asama_satirlarini_sec(
        rows, minimum_sample_size=minimum_sample_size
    )
    candidate_count = sum(row.candidate_count for row in rows)
    measured_count = sum(row.measured_count for row in rows)
    coverage = _rate(measured_count, candidate_count)
    best = max(
        reliable,
        key=lambda row: (row.success_rate_pct, row.measured_count, row.stage),
        default=None,
    )
    if measured_count == 0:
        note = "İleri performans henüz ölçülemedi."
    elif best is None:
        note = "Güvenilir aşama için örneklem yetersiz."
    else:
        note = "Sonuç gözlemseldir; üretim eşiği otomatik değiştirilmez."
    return PreBreakoutCalibrationSummary(
        candidate_count=candidate_count,
        measured_count=measured_count,
        measurement_coverage_pct=coverage,
        reliable_stage_count=len(reliable),
        best_stage=None if best is None else best.stage,
        best_stage_success_rate_pct=(
            0.0 if best is None else best.success_rate_pct
        ),
        sufficient_sample=bool(reliable),
        note=note,
    )


def _wilson_interval(successful: int, measured: int) -> tuple[float, float]:
    if measured < 0 or successful < 0 or successful > measured:
        raise ValueError("Başarılı ve ölçülen gözlem sayıları geçersiz.")
    if measured == 0:
        return (0.0, 0.0)
    z = 1.959963984540054
    proportion = successful / measured
    denominator = 1.0 + z * z / measured
    center = (proportion + z * z / (2.0 * measured)) / denominator
    margin = (
        z
        * sqrt(
            proportion * (1.0 - proportion) / measured
            + z * z / (4.0 * measured * measured)
        )
        / denominator
    )
    return (
        round(max(0.0, center - margin) * 100.0, 2),
        round(min(1.0, center + margin) * 100.0, 2),
    )


def asama_guven_araliklarini_hesapla(
    rows: Sequence[PreBreakoutCalibrationRow],
    *,
    minimum_sample_size: int = 3,
) -> tuple[PreBreakoutStageConfidenceRow, ...]:
    if minimum_sample_size < 1:
        raise ValueError("Minimum örneklem en az 1 olmalıdır.")
    values = []
    for row in rows:
        low, high = _wilson_interval(row.successful_count, row.measured_count)
        values.append(
            PreBreakoutStageConfidenceRow(
                stage=row.stage,
                measured_count=row.measured_count,
                successful_count=row.successful_count,
                success_rate_pct=row.success_rate_pct,
                confidence_low_pct=low,
                confidence_high_pct=high,
                sample_sufficient=row.measured_count >= minimum_sample_size,
                conservative_rank=None,
            )
        )
    reliable = sorted(
        (item for item in values if item.sample_sufficient),
        key=lambda item: (
            -item.confidence_low_pct,
            -item.success_rate_pct,
            -item.measured_count,
            item.stage,
        ),
    )
    ranks = {item.stage: rank for rank, item in enumerate(reliable, 1)}
    return tuple(
        replace(item, conservative_rank=ranks.get(item.stage))
        for item in values
    )


def temkinli_lider_asamayi_sec(
    rows: Sequence[PreBreakoutStageConfidenceRow],
) -> PreBreakoutStageConfidenceRow | None:
    reliable = [row for row in rows if row.conservative_rank is not None]
    return min(reliable, key=lambda row: row.conservative_rank, default=None)


def asama_guven_araliklarini_tabloya_cevir(
    rows: Sequence[PreBreakoutStageConfidenceRow],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Aşama": row.stage,
                "Ölçülen": row.measured_count,
                "Başarılı": row.successful_count,
                "Başarı oranı %": row.success_rate_pct,
                "%95 alt sınır": row.confidence_low_pct,
                "%95 üst sınır": row.confidence_high_pct,
                "Örneklem yeterli": "Evet" if row.sample_sufficient else "Hayır",
                "Temkinli sıra": row.conservative_rank,
            }
            for row in rows
        ]
    )


def lider_duyarlilik_senaryolarini_hesapla(
    rows: Sequence[PreBreakoutCalibrationRow],
    *,
    minimum_sample_size: int = 3,
) -> tuple[PreBreakoutLeaderSensitivityRow, ...]:
    baseline = temkinli_lider_asamayi_sec(
        asama_guven_araliklarini_hesapla(
            rows, minimum_sample_size=minimum_sample_size
        )
    )
    if baseline is None:
        return ()
    scenarios: list[PreBreakoutLeaderSensitivityRow] = []
    for row in rows:
        variants: list[tuple[str, PreBreakoutCalibrationRow]] = []
        if row.successful_count > 0:
            measured = row.measured_count - 1
            variants.append(
                (
                    "Başarılı gözlem",
                    replace(
                        row,
                        measured_count=measured,
                        successful_count=row.successful_count - 1,
                        success_rate_pct=_rate(row.successful_count - 1, measured),
                    ),
                )
            )
        if row.measured_count - row.successful_count > 0:
            measured = row.measured_count - 1
            variants.append(
                (
                    "Başarılı olmayan gözlem",
                    replace(
                        row,
                        measured_count=measured,
                        success_rate_pct=_rate(row.successful_count, measured),
                    ),
                )
            )
        for outcome, changed in variants:
            scenario_rows = tuple(changed if item is row else item for item in rows)
            leader = temkinli_lider_asamayi_sec(
                asama_guven_araliklarini_hesapla(
                    scenario_rows, minimum_sample_size=minimum_sample_size
                )
            )
            leader_stage = None if leader is None else leader.stage
            scenarios.append(
                PreBreakoutLeaderSensitivityRow(
                    stage=row.stage,
                    removed_outcome=outcome,
                    scenario_leader=leader_stage,
                    baseline_leader_retained=leader_stage == baseline.stage,
                )
            )
    return tuple(scenarios)


def lider_kararlilik_ozetini_hesapla(
    rows: Sequence[PreBreakoutCalibrationRow],
    *,
    minimum_sample_size: int = 3,
    stable_retention_pct: float = 80.0,
) -> PreBreakoutLeaderStabilitySummary:
    baseline = temkinli_lider_asamayi_sec(
        asama_guven_araliklarini_hesapla(
            rows, minimum_sample_size=minimum_sample_size
        )
    )
    if baseline is None:
        return PreBreakoutLeaderStabilitySummary(
            None, 0, 0, 0.0, False, "Lider kararlılığı ölçülemedi."
        )
    scenarios = lider_duyarlilik_senaryolarini_hesapla(
        rows, minimum_sample_size=minimum_sample_size
    )
    retained = sum(item.baseline_leader_retained for item in scenarios)
    retention = _rate(retained, len(scenarios))
    stable = bool(scenarios) and retention >= stable_retention_pct
    note = (
        "Temkinli lider tek gözlem duyarlılığında kararlı."
        if stable
        else "Temkinli lider tek gözlem değişimlerine karşı kırılgan."
    )
    return PreBreakoutLeaderStabilitySummary(
        baseline.stage,
        len(scenarios),
        retained,
        retention,
        stable,
        note,
    )


def lider_duyarlilik_senaryolarini_tabloya_cevir(
    rows: Sequence[PreBreakoutLeaderSensitivityRow],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Değiştirilen aşama": row.stage,
                "Çıkarılan sonuç": row.removed_outcome,
                "Senaryo lideri": row.scenario_leader,
                "Mevcut lider korundu": (
                    "Evet" if row.baseline_leader_retained else "Hayır"
                ),
            }
            for row in rows
        ]
    )


def _band_lower_bound(band: str) -> int:
    return int(str(band).split("-", 1)[0])


def kalibrasyon_esik_onerilerini_hesapla(
    stage_rows: Sequence[PreBreakoutCalibrationRow],
    momentum_rows: Sequence[PreBreakoutMomentumCalibrationRow],
    *,
    minimum_sample_size: int = 3,
    minimum_confidence_low_pct: float = 20.0,
) -> tuple[PreBreakoutThresholdRecommendation, ...]:
    if minimum_sample_size < 1:
        raise ValueError("Minimum örneklem en az 1 olmalıdır.")
    if not 0.0 <= minimum_confidence_low_pct <= 100.0:
        raise ValueError("Minimum güven alt sınırı 0 ile 100 arasında olmalıdır.")
    confidence = {
        item.stage: item
        for item in asama_guven_araliklarini_hesapla(
            stage_rows, minimum_sample_size=minimum_sample_size
        )
    }
    stability = lider_kararlilik_ozetini_hesapla(
        stage_rows, minimum_sample_size=minimum_sample_size
    )
    recommendations = []
    for row in stage_rows:
        interval = confidence[row.stage]
        bands = [
            item
            for item in momentum_rows
            if item.stage == row.stage
            and item.measured_count >= minimum_sample_size
        ]
        best_band = max(
            bands,
            key=lambda item: (
                item.success_rate_pct,
                item.measured_count,
                _band_lower_bound(item.momentum_band),
            ),
            default=None,
        )
        leader_stable = stability.stable and stability.baseline_leader == row.stage
        if not interval.sample_sufficient:
            action, threshold, evidence = "Veri biriktir", None, "Yetersiz"
            rationale = "Aşama örneklemi güvenilir öneri için yetersiz."
        elif interval.confidence_low_pct < minimum_confidence_low_pct:
            action, threshold, evidence = "Gevşetme önerilmez", None, "Zayıf"
            rationale = "Başarı oranının alt güven sınırı yetersiz."
        elif leader_stable and best_band is not None:
            action = "Kontrollü doğrulama adayı"
            threshold = _band_lower_bound(best_band.momentum_band)
            evidence = "Güçlü"
            rationale = "Kararlı temkinli lider ve yeterli momentum örneklemi."
        else:
            action, threshold, evidence = "Mevcut eşiği koru", None, "Sınırlı"
            rationale = "Eşik değişikliği için kararlı üstünlük oluşmadı."
        recommendations.append(
            PreBreakoutThresholdRecommendation(
                stage=row.stage,
                recommended_action=action,
                recommended_minimum_momentum_score=threshold,
                evidence_level=evidence,
                confidence_low_pct=interval.confidence_low_pct,
                measured_count=row.measured_count,
                leader_stable=leader_stable,
                auto_apply=False,
                rationale=rationale,
            )
        )
    return tuple(recommendations)


def kalibrasyon_esik_onerilerini_tabloya_cevir(
    rows: Sequence[PreBreakoutThresholdRecommendation],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Aşama": row.stage,
                "Önerilen işlem": row.recommended_action,
                "Önerilen minimum momentum": row.recommended_minimum_momentum_score,
                "Kanıt düzeyi": row.evidence_level,
                "%95 alt sınır": row.confidence_low_pct,
                "Ölçülen": row.measured_count,
                "Lider kararlı": "Evet" if row.leader_stable else "Hayır",
                "Otomatik uygulanır": "Evet" if row.auto_apply else "Hayır",
                "Gerekçe": row.rationale,
            }
            for row in rows
        ]
    )


def esik_onerilerini_tarihsel_dogrula(
    recommendations: Sequence[PreBreakoutThresholdRecommendation],
    momentum_rows: Sequence[PreBreakoutMomentumCalibrationRow],
    *,
    current_minimum_momentum_score: int = 10,
    minimum_candidate_sample_size: int = 3,
    minimum_sample_retention_pct: float = 50.0,
) -> tuple[PreBreakoutThresholdValidationRow, ...]:
    if minimum_candidate_sample_size < 1:
        raise ValueError("Minimum aday örneklemi en az 1 olmalıdır.")
    if not 0.0 <= minimum_sample_retention_pct <= 100.0:
        raise ValueError("Minimum örneklem korunma oranı geçersiz.")
    validations = []
    for recommendation in recommendations:
        proposed = recommendation.recommended_minimum_momentum_score
        if (
            recommendation.recommended_action != "Kontrollü doğrulama adayı"
            or proposed is None
        ):
            continue
        rows = [r for r in momentum_rows if r.stage == recommendation.stage]
        baseline_count = sum(r.measured_count for r in rows)
        baseline_successful = sum(r.successful_count for r in rows)
        candidate = [
            r for r in rows if _band_lower_bound(r.momentum_band) >= proposed
        ]
        candidate_count = sum(r.measured_count for r in candidate)
        candidate_successful = sum(r.successful_count for r in candidate)
        baseline_rate = _rate(baseline_successful, baseline_count)
        candidate_rate = _rate(candidate_successful, candidate_count)
        retention = _rate(candidate_count, baseline_count)
        confidence_low, _ = _wilson_interval(
            candidate_successful, candidate_count
        )
        if candidate_count < minimum_candidate_sample_size:
            verdict = "Örneklem yetersiz"
        elif retention < minimum_sample_retention_pct:
            verdict = "Aşırı örneklem kaybı"
        elif candidate_rate > baseline_rate:
            verdict = "Kontrollü uygulama adayı"
        else:
            verdict = "Üstünlük doğrulanmadı"
        validations.append(
            PreBreakoutThresholdValidationRow(
                stage=recommendation.stage,
                current_minimum_momentum_score=current_minimum_momentum_score,
                proposed_minimum_momentum_score=proposed,
                baseline_measured_count=baseline_count,
                baseline_success_rate_pct=baseline_rate,
                candidate_measured_count=candidate_count,
                candidate_success_rate_pct=candidate_rate,
                success_rate_delta_pct=round(candidate_rate - baseline_rate, 2),
                candidate_confidence_low_pct=confidence_low,
                sample_retention_pct=retention,
                verdict=verdict,
                auto_apply=False,
            )
        )
    return tuple(validations)


def esik_dogrulamalarini_tabloya_cevir(
    rows: Sequence[PreBreakoutThresholdValidationRow],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Aşama": row.stage,
                "Mevcut minimum momentum": row.current_minimum_momentum_score,
                "Önerilen minimum momentum": row.proposed_minimum_momentum_score,
                "Mevcut ölçülen": row.baseline_measured_count,
                "Mevcut başarı %": row.baseline_success_rate_pct,
                "Öneri ölçülen": row.candidate_measured_count,
                "Öneri başarı %": row.candidate_success_rate_pct,
                "Başarı farkı %": row.success_rate_delta_pct,
                "Öneri %95 alt sınır": row.candidate_confidence_low_pct,
                "Örneklem korunma %": row.sample_retention_pct,
                "Karar": row.verdict,
                "Otomatik uygulanır": "Evet" if row.auto_apply else "Hayır",
            }
            for row in rows
        ]
    )


def dogrulanmis_esik_politikasi_olustur(
    rows: Sequence[PreBreakoutThresholdValidationRow],
    *,
    enabled: bool = False,
) -> PreBreakoutThresholdPolicy:
    accepted = {
        row.stage: row.proposed_minimum_momentum_score
        for row in rows
        if row.verdict == "Kontrollü uygulama adayı"
    }
    return PreBreakoutThresholdPolicy(
        enabled=bool(enabled and accepted),
        stage_minimum_momentum_scores=accepted if enabled else {},
        source="Tarihsel kalibrasyon doğrulaması",
    )


# Sprint-88 Rev1 ile yayımlanan adlar geriye dönük uyumluluk için korunur.
from backend.app.prebreakout.prebreakout_score_threshold_calibration import (  # noqa: E402
    ThresholdCalibrationConfig,
    ThresholdCalibrationRecommendation,
    ThresholdCalibrationReport,
    calibration_thresholds,
    compare_thresholds,
    filter_records_for_threshold,
    generate_calibration_report,
    recommend_threshold,
)
