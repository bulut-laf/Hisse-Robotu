from dataclasses import dataclass


@dataclass(frozen=True)
class EV19FinalEV20FoundationState:
    symbol: str
    evolution_state: str
    lock_state: str
    foundation_state: str
    source: str = "EARLY_VISIBILITY"


def build_ev19_final_ev20_foundation_state(symbol: str):
    return EV19FinalEV20FoundationState(
        symbol=str(symbol).upper(),
        evolution_state="LOCKED",
        lock_state="READY",
        foundation_state="PREPARED",
    )
