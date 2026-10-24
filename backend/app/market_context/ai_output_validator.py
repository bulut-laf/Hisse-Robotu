from __future__ import annotations

import re
from typing import Any


REQUIRED_FIELDS = {
    "summary",
    "positive_factors",
    "risk_factors",
    "conflicting_points",
}

KNOWN_FIELDS = {
    "summary",
    "positive_factors",
    "risk_factors",
    "aligned_points",
    "conflicting_points",
    "watch_items",
}

FORBIDDEN_PATTERNS = [
    r"\bbuy\b",
    r"\bsell\b",
    r"\btechnical_score\b",
    r"\b(alınmalı|alınabilir|satılmalı|satılabilir)\b",
    r"\b(al|sat)\s+(hisse|pozisyon|sinyali)\b",
    r"\bal\s+fırsatı\b",
    r"\bsat\s+fırsatı\b",
    r"\bhedef\s+fiyat\b",
    r"\b(stop|stop[- ]loss|zarar\s+kes)\b",
    r"\bpozisyon\s+(aç|açılmalı|kapat|kapatılmalı)\b",
]


def _normalize_security_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value)

    text = text.lower()

    # Eski UTF-8/encoding bozulmalarında görülen "Д±" dizisi
    # lower() sonrasında "д±" olur. Güvenlik taramasında gerçek
    # Türkçe noktasız ı karakterine normalize edilir.
    text = text.replace("д±", "ı")

    return text


def _contains_trade_instruction(value: Any) -> bool:
    text = _normalize_security_text(value)

    return any(
        re.search(pattern, text)
        for pattern in FORBIDDEN_PATTERNS
    )


def validate_ai_output(
    output: dict[str, Any],
) -> bool:
    """AI çıktı güvenlik doğrulaması."""

    if not isinstance(output, dict):
        return False

    if not REQUIRED_FIELDS.issubset(output.keys()):
        return False

    if "technical_score" in output:
        return False

    for key in KNOWN_FIELDS:
        if key not in output:
            continue

        value = output[key]

        if key == "summary":
            if value is not None and not isinstance(value, str):
                return False
        elif not isinstance(value, list):
            return False

        if _contains_trade_instruction(value):
            return False

    for key, value in output.items():
        if key not in KNOWN_FIELDS and _contains_trade_instruction(value):
            return False

    return True
