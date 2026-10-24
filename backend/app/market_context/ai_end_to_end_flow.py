from __future__ import annotations

from typing import Any

from backend.app.market_context.ai_evaluation_service import (
    process_ai_evaluation_response,
)


def run_ai_evaluation_flow(
    response: dict[str, Any],
) -> dict[str, Any]:
    """AI değerlendirme zinciri son test akışı.

    Gerçek AI çağrısı yapmaz.
    Hazırlanan servis zincirini doğrular.
    """

    result = process_ai_evaluation_response(response)

    return {
        "pipeline": "ai_evaluation_v1",
        "result": result,
    }
