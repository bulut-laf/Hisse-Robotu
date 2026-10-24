from __future__ import annotations

import re
from typing import Any


REQUIRED_FIELDS = {
    "summary",
    "positive_factors",
    "risk_factors",
    "conflicting_points",
}


FORBIDDEN_PATTERNS = [
    r"\bbuy\b",
    r"\bsell\b",
    r"\btechnical_score\b",
    r"\b(alınmalı|alınabilir|satılmalı|satılabilir)\b",
    r"\b(al|sat)\s+(hisse|pozisyon|sinyali)\b",
    r"\bal\s+fırsatı\b",
    r"\bsat\s+fırsatı\b",
]


def _contains_trade_instruction(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, list):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value)

    text = text.lower()

    return any(
        re.search(pattern, text)
        for pattern in FORBIDDEN_PATTERNS
    )


def validate_ai_output(
    output: dict[str, Any],
) -> bool:
    """AI çıktı güvenlik doğrulaması.

    İşlem kararı üretmez.
    Sadece format ve işlem dili kontrolü yapar.
    """

    if not REQUIRED_FIELDS.issubset(output.keys()):
        return False

    for key, value in output.items():

        if key == "technical_score":
            return False

        if _contains_trade_instruction(value):
            return False

    return True