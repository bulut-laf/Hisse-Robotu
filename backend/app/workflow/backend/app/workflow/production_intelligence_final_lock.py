from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionIntelligenceFinalLock:
    symbol: str
    intelligence_state: str
    observation_state: str
    optimization_state: str
    readiness_state: str
    monitoring_state: str
    quality_state: str
    source: str = "EARLY_VISIBILITY"


def build_production_intelligence_lock(symbol: str):
    return ProductionIntelligenceFinalLock(
        symbol=str(symbol).upper(),
        intelligence_state="LOCKED",
        observation_state="ACTIVE",
        optimization_state="STABLE",
        readiness_state="READY",
        monitoring_state="CLOSED",
        quality_state="CLOSED",
    )


def build_production_intelligence_final_lock(symbol: str):
    return build_production_intelligence_lock(symbol)
