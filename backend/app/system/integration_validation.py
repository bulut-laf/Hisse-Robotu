from __future__ import annotations

from typing import Any


def validate_system_integration(
    modules: dict[str, Any],
) -> dict[str, Any]:
    """Ana modüllerin entegrasyon durumunu kontrol eder."""

    checks = {
        name: bool(status)
        for name, status in modules.items()
    }

    return {
        "checks": checks,
        "ready": all(checks.values()) if checks else False,
    }
