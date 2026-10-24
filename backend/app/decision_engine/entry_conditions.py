from __future__ import annotations

from typing import Any


def evaluate_entry_conditions(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Giriş koşullarını değerlendirir.

    Karar desteği sağlar.
    Tek başına işlem emri üretmez.
    """

    checks = {
        "market": context.get("market") == "positive",
        "sector": context.get("sector") == "strong",
        "technical": context.get("technical") == "positive",
        "momentum": context.get("momentum") == "positive",
        "risk": context.get("risk") == "controlled",
    }

    passed = sum(checks.values())

    return {
        "checks": checks,
        "passed_count": passed,
        "entry_candidate": passed >= 4,
    }
