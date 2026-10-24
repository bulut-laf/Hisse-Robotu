from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityFinalization:
    symbol: str
    feedback_quality: str
    observation_linked: bool
    lifecycle_status: str
    source: str = "EARLY_VISIBILITY"


def finalize_early_visibility_flow(symbol: str):
    return EarlyVisibilityFinalization(
        symbol=str(symbol).upper(),
        feedback_quality="VALIDATED",
        observation_linked=True,
        lifecycle_status="CLOSED",
    )
