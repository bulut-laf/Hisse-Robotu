from __future__ import annotations

from typing import Any


def _factor_list(
    item: dict[str, Any],
    key: str,
) -> list[str]:
    output = item.get("output")
    source = output if isinstance(output, dict) else item
    values = source.get(key, [])

    if not isinstance(values, list):
        return []

    return [
        str(value).strip()
        for value in values
        if str(value).strip()
    ]


def _normalised_set(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}

    for value in values:
        result.setdefault(value.casefold(), value)

    return result


def analyze_ai_history_trend(
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """AI değerlendirme geçmişindeki eğilimleri çıkarır.

    Eski frekans alanlarını korur. Buna ek olarak son güne göre yeni,
    kaybolan ve kalıcı risk/olumlu faktörleri üretir.
    """

    if not history:
        return {
            "count": 0,
            "risk_frequency": {},
            "positive_frequency": {},
            "persistent_risks": [],
            "new_risks": [],
            "resolved_risks": [],
            "persistent_positive_factors": [],
            "new_positive_factors": [],
            "lost_positive_factors": [],
            "direction": "veri_yok",
        }

    risk_frequency: dict[str, int] = {}
    positive_frequency: dict[str, int] = {}

    risk_display: dict[str, str] = {}
    positive_display: dict[str, str] = {}

    for item in history:
        for risk in _factor_list(item, "risk_factors"):
            key = risk.casefold()
            risk_display.setdefault(key, risk)
            risk_frequency[risk_display[key]] = (
                risk_frequency.get(risk_display[key], 0) + 1
            )

        for positive in _factor_list(item, "positive_factors"):
            key = positive.casefold()
            positive_display.setdefault(key, positive)
            positive_frequency[positive_display[key]] = (
                positive_frequency.get(positive_display[key], 0) + 1
            )

    previous = history[-2] if len(history) >= 2 else None
    current = history[-1]

    current_risks = _normalised_set(
        _factor_list(current, "risk_factors")
    )
    previous_risks = _normalised_set(
        _factor_list(previous, "risk_factors")
        if previous
        else []
    )

    current_positive = _normalised_set(
        _factor_list(current, "positive_factors")
    )
    previous_positive = _normalised_set(
        _factor_list(previous, "positive_factors")
        if previous
        else []
    )

    current_risk_keys = set(current_risks)
    previous_risk_keys = set(previous_risks)
    current_positive_keys = set(current_positive)
    previous_positive_keys = set(previous_positive)

    persistent_risks = [
        current_risks[key]
        for key in sorted(current_risk_keys & previous_risk_keys)
    ]
    new_risks = [
        current_risks[key]
        for key in sorted(current_risk_keys - previous_risk_keys)
    ]
    resolved_risks = [
        previous_risks[key]
        for key in sorted(previous_risk_keys - current_risk_keys)
    ]

    persistent_positive = [
        current_positive[key]
        for key in sorted(
            current_positive_keys & previous_positive_keys
        )
    ]
    new_positive = [
        current_positive[key]
        for key in sorted(
            current_positive_keys - previous_positive_keys
        )
    ]
    lost_positive = [
        previous_positive[key]
        for key in sorted(
            previous_positive_keys - current_positive_keys
        )
    ]

    if len(history) < 2:
        direction = "baslangic_verisi"
    elif new_risks and not new_positive:
        direction = "risk_artiyor"
    elif new_positive and not new_risks:
        direction = "olumlu_gucleniyor"
    elif new_risks or new_positive:
        direction = "karisik"
    else:
        direction = "dengeli"

    return {
        "count": len(history),
        "risk_frequency": risk_frequency,
        "positive_frequency": positive_frequency,
        "persistent_risks": persistent_risks,
        "new_risks": new_risks,
        "resolved_risks": resolved_risks,
        "persistent_positive_factors": persistent_positive,
        "new_positive_factors": new_positive,
        "lost_positive_factors": lost_positive,
        "direction": direction,
    }
