from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


CANONICAL_FAMILIES = (
    "research_score_direction",
    "trend",
    "momentum",
    "relative_strength",
    "setup",
    "entry_breakout_readiness",
)


@dataclass(frozen=True)
class QualityEvidence:
    family: str
    state: str
    source_module: str
    detail: str = ""


@dataclass(frozen=True)
class EarlyVisibilityQualityContext:
    symbol: str
    status: str
    evidence: tuple[QualityEvidence, ...]
    unique_family_count: int
    next_review_module: str
    data_blocked: bool


def _normalize(value: object) -> str:
    return str(value or "").strip().casefold()


def _is_positive(state: str) -> bool:
    value = _normalize(state)
    return value in {
        "positive",
        "pozitif",
        "strong",
        "guclu",
        "güçlü",
        "strengthening",
        "gucleniyor",
        "güçleniyor",
        "supported",
        "destekleniyor",
        "ready",
        "hazir",
        "hazır",
        "confirmed",
        "teyitli",
    }


def _is_weak(state: str) -> bool:
    value = _normalize(state)
    return value in {
        "negative",
        "negatif",
        "weak",
        "zayif",
        "zayıf",
        "deteriorating",
        "bozuluyor",
        "not_ready",
        "hazir_degil",
        "hazır_değil",
    }


def deduplicate_canonical_evidence(
    evidence: Iterable[QualityEvidence],
) -> tuple[QualityEvidence, ...]:
    """Keep one observation per canonical family.

    Source modules are not votes. When the same family appears repeatedly,
    the first canonical observation is preserved and duplicates are ignored.
    """
    seen: set[str] = set()
    result: list[QualityEvidence] = []

    for item in evidence:
        family = _normalize(item.family)
        if family not in CANONICAL_FAMILIES:
            continue
        if family in seen:
            continue
        seen.add(family)
        result.append(
            QualityEvidence(
                family=family,
                state=item.state,
                source_module=item.source_module,
                detail=item.detail,
            )
        )
    return tuple(result)


def _quality_status(evidence: tuple[QualityEvidence, ...], *, data_blocked: bool) -> str:
    if data_blocked:
        return "VERI_BLOKLU"
    if not evidence:
        return "TEYITSIZ"

    positive = sum(_is_positive(item.state) for item in evidence)
    weak = sum(_is_weak(item.state) for item in evidence)

    if positive == 0 and weak > 0:
        return "ZAYIF"
    if positive >= 3 and weak == 0:
        return "DESTEKLENIYOR"
    if positive >= 1:
        return "GUCLENIYOR"
    return "TEYITSIZ"


def next_review_module(
    evidence: Iterable[QualityEvidence],
    *,
    data_blocked: bool = False,
) -> str:
    if data_blocked:
        return "Gecikmeli Veri Pilotu"

    by_family = {
        _normalize(item.family): item
        for item in deduplicate_canonical_evidence(evidence)
    }

    setup = by_family.get("setup")
    readiness = by_family.get("entry_breakout_readiness")
    momentum = by_family.get("momentum")

    if setup is not None and (_is_positive(setup.state) or not _is_weak(setup.state)):
        return "Ön Yükseliş Hazırlık"
    if readiness is not None and _is_positive(readiness.state):
        return "Fırsat Radarı"
    if momentum is not None:
        return "Momentum Keşif"
    return "Ana Research Sıralaması"


def build_quality_context(
    *,
    symbol: str,
    evidence: Iterable[QualityEvidence],
    data_blocked: bool = False,
) -> EarlyVisibilityQualityContext:
    unique = deduplicate_canonical_evidence(evidence)
    return EarlyVisibilityQualityContext(
        symbol=str(symbol).removesuffix(".IS").upper().strip(),
        status=_quality_status(unique, data_blocked=data_blocked),
        evidence=unique,
        unique_family_count=len(unique),
        next_review_module=next_review_module(unique, data_blocked=data_blocked),
        data_blocked=data_blocked,
    )


def evidence_from_mapping(
    *,
    source_module: str,
    values: Mapping[str, object],
) -> tuple[QualityEvidence, ...]:
    """Adapter for existing canonical outputs.

    This function does not calculate factors. It only labels already-computed
    values with their canonical family so they can be displayed once.
    """
    items: list[QualityEvidence] = []
    for family, state in values.items():
        normalized = _normalize(family)
        if normalized not in CANONICAL_FAMILIES:
            continue
        items.append(
            QualityEvidence(
                family=normalized,
                state=str(state),
                source_module=source_module,
            )
        )
    return tuple(items)
