from __future__ import annotations

from typing import Any


def evaluate_v1_usage(
    status: dict[str, Any],
) -> dict[str, Any]:
    """V1 kullanım değerlendirme kontrolü."""

    checks = {
        "technical": bool(status.get("technical")),
        "usability": bool(status.get("usability")),
        "explainability": bool(status.get("explainability")),
        "stability": bool(status.get("stability")),
    }

    return {
        "checks": checks,
        "ready": all(checks.values()) if checks else False,
    }
