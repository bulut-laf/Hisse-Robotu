from dataclasses import dataclass


@dataclass(frozen=True)
class ContinuousOptimizationLoopState:
    symbol: str
    feedback_state: str
    mapping_state: str
    calibration_state: str
    maturity_state: str
    source: str = "EARLY_VISIBILITY"


def build_continuous_optimization_loop_state(symbol: str):
    return ContinuousOptimizationLoopState(
        symbol=str(symbol).upper(),
        feedback_state="CONNECTED",
        mapping_state="TRACKING",
        calibration_state="ACTIVE",
        maturity_state="FOUNDATION",
    )
