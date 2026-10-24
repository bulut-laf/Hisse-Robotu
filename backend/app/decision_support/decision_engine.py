from __future__ import annotations

from typing import Any


def evaluate_decision_context(
    market_state: str,
    sector_state: str,
    technical_state: str,
    risk_state: str,
) -> dict[str, Any]:
    """Birleşik karar değerlendirme hazırlığı.

    Tüm bağlamları bir araya getirir.
    Nihai işlem emri üretmez.
    """

    positive = (
        market_state == "positive"
        and sector_state == "strong"
        and technical_state == "positive"
        and risk_state == "controlled"
    )

    if positive:
        decision = "candidate"
    else:
        decision = "watch"

    return {
        "decision": decision,
        "market_state": market_state,
        "sector_state": sector_state,
        "technical_state": technical_state,
        "risk_state": risk_state,
    }
