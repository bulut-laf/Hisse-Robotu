from __future__ import annotations

from typing import Any


def run_user_acceptance_validation(
    modules: dict[str, Any],
) -> dict[str, Any]:
    """Milestone kullanıcı kabul kontrolü."""

    checks = {
        key: bool(value)
        for key, value in modules.items()
    }

    return {
        "checks": checks,
        "accepted": all(checks.values()) if checks else False,
    }
