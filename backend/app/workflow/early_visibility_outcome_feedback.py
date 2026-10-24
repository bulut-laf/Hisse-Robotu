from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityOutcomeFeedback:
    symbol: str
    outcome: str
    feedback_state: str
    source: str = "EARLY_VISIBILITY"


def build_early_visibility_outcome_feedback(symbol: str, outcome: str):
    return EarlyVisibilityOutcomeFeedback(
        symbol=str(symbol).upper(),
        outcome=str(outcome).upper(),
        feedback_state="RECORDED",
    )
