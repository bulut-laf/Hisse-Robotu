from dataclasses import dataclass


@dataclass(frozen=True)
class IntelligenceCalibrationState:
    symbol: str
    calibration_state: str
    historical_state: str
    quality_trend: str
    source: str = "EARLY_VISIBILITY"


def build_intelligence_calibration_state(symbol: str):
    return IntelligenceCalibrationState(
        symbol=str(symbol).upper(),
        calibration_state="TRACKING",
        historical_state="PREPARED",
        quality_trend="OBSERVED",
    )
