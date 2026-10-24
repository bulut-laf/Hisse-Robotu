from dataclasses import dataclass


@dataclass(frozen=True)
class LongTermIntelligenceState:
    symbol: str
    memory_state: str
    historical_state: str
    persistence_state: str
    source: str = "EARLY_VISIBILITY"


def build_long_term_intelligence_state(symbol: str):
    return LongTermIntelligenceState(
        symbol=str(symbol).upper(),
        memory_state="FOUNDATION",
        historical_state="PREPARED",
        persistence_state="FOUNDATION",
    )
