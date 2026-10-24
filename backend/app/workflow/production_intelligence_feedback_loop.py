from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionIntelligenceFeedbackState:
    symbol: str
    feedback_state: str
    improvement_state: str
    calibration_state: str
    source: str = "EARLY_VISIBILITY"


def build_production_intelligence_feedback_state(symbol: str):
    return ProductionIntelligenceFeedbackState(
        symbol=str(symbol).upper(),
        feedback_state="COLLECTING",
        improvement_state="MAPPED",
        calibration_state="TRACKING",
    )
