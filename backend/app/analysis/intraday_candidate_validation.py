from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


CandidateValidationState = Literal[
    "ADAY_DESTEKLENIYOR",
    "ADAY_DESTEKLENMIYOR",
    "VERI_YETERSIZ",
]


@dataclass(frozen=True)
class IntradayCandidateValidation:
    state: CandidateValidationState
    reason: str


def validate_intraday_candidate(
    evidence: object,
    freshness: object,
) -> IntradayCandidateValidation:
    freshness_state = freshness.state
    preview_only = getattr(freshness, "preview_only", False)

    if freshness_state in {
        "DATA_KILITLI",
        "DATA_YETERSIZ",
    }:
        return IntradayCandidateValidation(
            state="VERI_YETERSIZ",
            reason=f"Intraday veri durumu: {freshness_state}.",
        )

    if (
        freshness_state == "DATA_GECIKMELI"
        and not preview_only
    ):
        return IntradayCandidateValidation(
            state="VERI_YETERSIZ",
            reason="Gecikmeli veri preview modunda degil.",
        )

    movement_structure = evidence.movement_structure
    volume_state = evidence.volume_state

    if movement_structure in {
        "POZITIF_SUREKLI",
        "TOPARLANIYOR",
    } and volume_state == "DESTEKLIYOR":
        return IntradayCandidateValidation(
            state="ADAY_DESTEKLENIYOR",
            reason=(
                f"{movement_structure} + "
                "DESTEKLIYOR."
            ),
        )

    return IntradayCandidateValidation(
        state="ADAY_DESTEKLENMIYOR",
        reason=(
            f"{movement_structure} + "
            f"{volume_state}."
        ),
    )
