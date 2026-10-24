from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuousIntelligenceExpansionState:
    symbol: str
    expansion_state: str
    intelligence_state: str
    foundation_state: str
    source: str = "EARLY_VISIBILITY"


def build_continuous_intelligence_expansion_state(symbol: str):
    return ContinuousIntelligenceExpansionState(
        symbol=str(symbol).upper(),
        expansion_state="TRACKING",
        intelligence_state="EVOLVING",
        foundation_state="READY",
    )
