from dataclasses import dataclass


@dataclass(frozen=True)
class EV20FinalEV21FoundationState:
    symbol: str
    maturity_state: str
    readiness_state: str
    foundation_state: str
    source: str = "EARLY_VISIBILITY"


def build_ev20_final_ev21_foundation_state(symbol: str):
    return EV20FinalEV21FoundationState(
        symbol=str(symbol).upper(),
        maturity_state="LOCKED",
        readiness_state="READY",
        foundation_state="PREPARED",
    )
