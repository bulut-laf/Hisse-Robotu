from __future__ import annotations

from typing import Any


def build_ai_history_view(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """AI geçmiş kayıtlarını kullanıcı görünümü için hazırlar.

    Karar veya işlem sinyali üretmez.
    Sadece okunabilir geçmiş verisi oluşturur.
    """

    return [
        {
            "date": item.get("date"),
            "summary": item.get("summary"),
            "risk_factors": list(item.get("risk_factors", [])),
            "positive_factors": list(item.get("positive_factors", [])),
        }
        for item in records
    ]
