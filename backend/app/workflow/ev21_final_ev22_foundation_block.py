from dataclasses import dataclass


@dataclass(frozen=True)
class EV21FinalEV22FoundationState:
    symbol: str
    adaptation_state: str
    lock_state: str
    foundation_state: str
    source: str = "EARLY_VISIBILITY"


def build_ev21_final_ev22_foundation_state(symbol: str):
    return EV21FinalEV22FoundationState(
        symbol=str(symbol).upper(),
        adaptation_state="LOCKED",
        lock_state="READY",
        foundation_state="PREPARED",
    )
