from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EarlyVisibilityHardeningResult:
    symbol: str
    status: str
    source: str = "EARLY_VISIBILITY"


def harden_early_visibility_operation(symbol: str) -> EarlyVisibilityHardeningResult:
    return EarlyVisibilityHardeningResult(
        symbol=str(symbol).upper(),
        status="READY",
    )
