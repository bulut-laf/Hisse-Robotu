from __future__ import annotations

from typing import Any


def validate_signal_quality(
    signal: dict[str, Any],
) -> dict[str, Any]:
    """Sinyal kalitesi ve denge kontrolü."""

    checks = {
        "decision": bool(signal.get("decision")),
        "score": signal.get("score") is not None,
        "risk": bool(signal.get("risk")),
        "reason": bool(signal.get("reason")),
    }

    return {
        "checks": checks,
        "ready": all(checks.values()) if checks else False,
    }
