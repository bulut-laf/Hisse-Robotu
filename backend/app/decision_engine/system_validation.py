from __future__ import annotations

from typing import Any


def validate_decision_system(
    components: dict[str, Any],
) -> dict[str, Any]:
    """Karar sistemi bileşenlerinin genel doğrulamasını yapar."""

    checks = {
        key: bool(value)
        for key, value in components.items()
    }

    return {
        "checks": checks,
        "ready": all(checks.values()) if checks else False,
    }
