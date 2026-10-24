from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionQualityAnalyticsState:
    symbol: str
    false_positive_state: str
    accuracy_state: str
    outcome_state: str
    metric_state: str
    source: str = "EARLY_VISIBILITY"


def build_production_quality_analytics_state(symbol: str):
    return ProductionQualityAnalyticsState(
        symbol=str(symbol).upper(),
        false_positive_state="TRACKING",
        accuracy_state="OBSERVED",
        outcome_state="MEASURED",
        metric_state="FOUNDATION",
    )
