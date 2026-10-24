from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionIntelligenceObservation:
    symbol: str
    usage_state: str
    quality_state: str
    source: str = "EARLY_VISIBILITY"


def build_production_intelligence_observation(symbol: str):
    return ProductionIntelligenceObservation(
        symbol=str(symbol).upper(),
        usage_state="OBSERVED",
        quality_state="TRACKING",
    )
