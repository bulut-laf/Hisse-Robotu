from __future__ import annotations

from typing import Any


def evaluate_exit_conditions(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Çıkış ve risk koşullarını değerlendirir.

    Pozisyon yönetimi için karar desteği sağlar.
    Tek başına işlem emri üretmez.
    """

    checks = {
        "trend_break": context.get("trend") == "broken",
        "momentum_loss": context.get("momentum") == "negative",
        "risk_increase": context.get("risk") == "high",
        "market_change": context.get("market") == "negative",
    }

    exit_score = sum(checks.values())

    return {
        "checks": checks,
        "exit_score": exit_score,
        "exit_candidate": exit_score >= 2,
    }
