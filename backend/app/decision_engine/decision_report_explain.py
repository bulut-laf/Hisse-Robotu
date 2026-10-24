from __future__ import annotations

from typing import Any


def build_explainable_decision_report(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Karar sonucunu gerekçeleriyle birlikte hazırlar.

    Açıklanabilir karar desteği sağlar.
    Tek başına işlem emri üretmez.
    """

    reasons = []

    if context.get("sector") == "strong":
        reasons.append("Güçlü sektör desteği")

    if context.get("technical") == "positive":
        reasons.append("Pozitif teknik görünüm")

    if context.get("risk") == "controlled":
        reasons.append("Kontrollü risk seviyesi")

    return {
        "symbol": context.get("symbol"),
        "decision": context.get("decision"),
        "reasons": reasons,
        "confidence": context.get("confidence", "medium"),
    }
