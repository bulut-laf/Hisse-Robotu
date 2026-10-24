from __future__ import annotations

from typing import Any


def connect_analysis_to_decision(
    analysis: dict[str, Any],
) -> dict[str, Any]:
    """Mevcut analiz çıktısını karar motoru giriş formatına bağlar.

    Entegrasyon katmanıdır.
    Tek başına işlem emri üretmez.
    """

    return {
        "symbol": analysis.get("symbol"),
        "market": analysis.get("market"),
        "sector": analysis.get("sector"),
        "technical": analysis.get("technical"),
        "risk": analysis.get("risk"),
        "score": analysis.get("score", 0),
    }
