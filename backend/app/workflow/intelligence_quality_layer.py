from dataclasses import dataclass


@dataclass(frozen=True)
class IntelligenceQualityObservation:
    symbol: str
    false_positive_state: str
    metric_state: str
    calibration_state: str
    source: str = "EARLY_VISIBILITY"


def build_intelligence_quality_observation(symbol: str):
    return IntelligenceQualityObservation(
        symbol=str(symbol).upper(),
        false_positive_state="OBSERVED",
        metric_state="TRACKING",
        calibration_state="FOUNDATION",
    )
