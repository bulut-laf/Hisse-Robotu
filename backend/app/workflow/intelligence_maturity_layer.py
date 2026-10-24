from dataclasses import dataclass


@dataclass(frozen=True)
class IntelligenceMaturityState:
    symbol: str
    maturity_state: str
    optimization_state: str
    quality_state: str
    readiness_state: str
    source: str = "EARLY_VISIBILITY"


def build_intelligence_maturity_state(symbol: str):
    return IntelligenceMaturityState(
        symbol=str(symbol).upper(),
        maturity_state="TRACKING",
        optimization_state="ACTIVE",
        quality_state="OBSERVED",
        readiness_state="PREPARED",
    )
