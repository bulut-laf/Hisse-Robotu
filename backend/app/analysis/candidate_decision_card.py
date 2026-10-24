from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateDecisionCard:
    symbol: str
    reasons: tuple[str, ...]
    risks: tuple[str, ...]
    next_module: str


def build_candidate_decision_card(candidate: object) -> CandidateDecisionCard:
    return CandidateDecisionCard(
        symbol=str(getattr(candidate, "symbol", "")).upper(),
        reasons=tuple(getattr(candidate, "reasons", ())),
        risks=tuple(getattr(candidate, "risks", ())),
        next_module="GÜNCEL TEKNİK ANALİZ",
    )
