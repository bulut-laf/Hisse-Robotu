from __future__ import annotations

from typing import Any


def prepare_ai_analysis_request(
    daily_package: dict[str, Any],
) -> dict[str, Any]:
    """Gerçek AI yorumlama katmanı için istek hazırlığı.

    Bu sürüm AI çağrısı yapmaz.
    Sadece standart analiz girdisi oluşturur.
    """

    return {
        "ready": True,
        "context": daily_package,
        "instruction": "Analyze market context only.",
    }
