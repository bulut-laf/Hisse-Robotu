from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .evidence_mapper import EvidenceState, FundEvidenceMap

FUND_ANALYSIS_ENGINE_VERSION = "fund-analysis-v1"


class FundAnalysisClass(str, Enum):
    A = "A"  # GL / NCELKL
    B = "B"  # GELŞEN
    C = "C"  # ZLE
    D = "D"  # ZAYIFLAYAN
    X = "X"  # UYGUN DEL


CLASS_LABELS = {
    FundAnalysisClass.A: "GL / NCELKL",
    FundAnalysisClass.B: "GELŞEN",
    FundAnalysisClass.C: "ZLE",
    FundAnalysisClass.D: "ZAYIFLAYAN",
    FundAnalysisClass.X: "UYGUN DEL",
}


@dataclass(frozen=True, slots=True)
class FundAnalysisResult:
    canonical_fund_id: str
    category_id: str | None
    classification: FundAnalysisClass
    class_label: str
    positive_families: tuple[str, ...]
    neutral_families: tuple[str, ...]
    caution_families: tuple[str, ...]
    unavailable_families: tuple[str, ...]
    eligibility_reason: str
    explanation: str
    automatic_trade_authority: str = "NONE"
    forced_fill: bool = False
    engine_version: str = FUND_ANALYSIS_ENGINE_VERSION


def analyze_fund(evidence_map: FundEvidenceMap) -> FundAnalysisResult:
    buckets = {
        state: tuple(item.family for item in evidence_map.evidence if item.state is state)
        for state in EvidenceState
    }
    positive = buckets[EvidenceState.POSITIVE]
    neutral = buckets[EvidenceState.NEUTRAL]
    caution = buckets[EvidenceState.CAUTION]
    unavailable = buckets[EvidenceState.UNAVAILABLE]
    available_count = len(positive) + len(neutral) + len(caution)

    if evidence_map.category_mapping_state != "MAPPED":
        classification = FundAnalysisClass.X
        reason = "CATEGORY_UNMAPPED"
    elif available_count < 3:
        classification = FundAnalysisClass.X
        reason = "INSUFFICIENT_INDEPENDENT_EVIDENCE"
    elif len(caution) >= 2 or ("F1" in caution and "F2" in caution):
        classification = FundAnalysisClass.D
        reason = "MULTI_FAMILY_WEAKENING"
    elif (
        available_count >= 4
        and len(positive) >= 4
        and ("F1" in positive or "F2" in positive)
        and not caution
    ):
        classification = FundAnalysisClass.A
        reason = "BROAD_STRENGTH_WITH_RELATIVE_OR_TREND_CONFIRMATION"
    elif available_count >= 3 and len(positive) >= 2 and len(caution) <= 1:
        classification = FundAnalysisClass.B
        reason = "DEVELOPING_MULTI_FAMILY_SUPPORT"
    else:
        classification = FundAnalysisClass.C
        reason = "OBSERVATION_REQUIRED"

    explanation = (
        f"{CLASS_LABELS[classification]} · pozitif={','.join(positive) or '-'} · "
        f"nötr={','.join(neutral) or '-'} · dikkat={','.join(caution) or '-'} · "
        f"eksik={','.join(unavailable) or '-'}"
    )
    return FundAnalysisResult(
        canonical_fund_id=evidence_map.canonical_fund_id,
        category_id=evidence_map.category_id,
        classification=classification,
        class_label=CLASS_LABELS[classification],
        positive_families=positive,
        neutral_families=neutral,
        caution_families=caution,
        unavailable_families=unavailable,
        eligibility_reason=reason,
        explanation=explanation,
    )


def analyze_funds(items: tuple[FundEvidenceMap, ...]) -> tuple[FundAnalysisResult, ...]:
    """Input sırasından bağımsız deterministic çıktı; sınıf kotası/fill yoktur."""
    unique: dict[str, FundEvidenceMap] = {}
    for item in items:
        if item.canonical_fund_id in unique:
            raise ValueError(f"DUPLICATE_FUND:{item.canonical_fund_id}")
        unique[item.canonical_fund_id] = item
    return tuple(analyze_fund(unique[key]) for key in sorted(unique))
