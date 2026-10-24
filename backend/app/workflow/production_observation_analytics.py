from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionObservationAnalyticsState:
    symbol: str
    observation_state: str
    quality_state: str
    analytics_state: str
    source: str = "EARLY_VISIBILITY"


def build_production_observation_analytics_state(symbol: str):
    return ProductionObservationAnalyticsState(
        symbol=str(symbol).upper(),
        observation_state="ACTIVE",
        quality_state="TRACKING",
        analytics_state="FOUNDATION",
    )
