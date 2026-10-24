from dataclasses import dataclass


@dataclass(frozen=True)
class FinalIntelligenceMaturityState:
    symbol: str
    maturity_state: str
    autonomy_state: str
    optimization_state: str
    readiness_state: str
    source: str = "EARLY_VISIBILITY"


def build_final_intelligence_maturity_state(symbol: str):
    return FinalIntelligenceMaturityState(
        symbol=str(symbol).upper(),
        maturity_state="ADVANCED",
        autonomy_state="FOUNDATION",
        optimization_state="ACTIVE",
        readiness_state="PREPARED",
    )
