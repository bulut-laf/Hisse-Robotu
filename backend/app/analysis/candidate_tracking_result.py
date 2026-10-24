from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateTrackingResult:
    symbol: str
    tracking_state: str
    result_state: str
    next_step: str


def build_candidate_tracking_result(candidate: object) -> CandidateTrackingResult:
    return CandidateTrackingResult(
        symbol=str(getattr(candidate, "symbol", "")).upper(),
        tracking_state=str(
            getattr(candidate, "tracking_state", "BEKLEMEDE")
        ),
        result_state=str(
            getattr(candidate, "result_state", "BEKLEMEDE")
        ),
        next_step="GÜN SONU DEĞERLENDİRME",
    )
