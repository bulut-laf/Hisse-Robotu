from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuousLearningAnalyticsState:
    symbol: str
    pattern_state: str
    feedback_metric_state: str
    learning_state: str
    evolution_state: str
    source: str = "EARLY_VISIBILITY"


def build_continuous_learning_analytics_state(symbol: str):
    return ContinuousLearningAnalyticsState(
        symbol=str(symbol).upper(),
        pattern_state="OBSERVED",
        feedback_metric_state="FOUNDATION",
        learning_state="TRACKING",
        evolution_state="PREPARED",
    )
