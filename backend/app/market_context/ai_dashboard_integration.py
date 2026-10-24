from __future__ import annotations

from typing import Any

from backend.app.market_context.ai_dashboard_provider import (
    build_ai_dashboard_payload,
)


def build_ai_dashboard_view(
    evaluation: dict[str, Any] | None,
) -> dict[str, Any]:
    """AI dashboard entegrasyon akışı hazırlığı.

    Kullanıcı görünümü için veri birleştirir.
    İşlem kararı üretmez.
    """

    payload = build_ai_dashboard_payload(evaluation)

    return {
        "component": "ai_market_context_card",
        "payload": payload,
    }
