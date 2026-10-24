from __future__ import annotations

from typing import Any


def _read_output(item: dict[str, Any]) -> dict[str, Any]:
    output = item.get("output")
    if isinstance(output, dict):
        return output
    return item


def build_ai_history_view(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """AI geçmiş kayıtlarını kullanıcı görünümü için hazırlar.

    Eski düz kayıtları ve Sprint-139C'nin ``output`` içeren kayıt biçimini
    birlikte destekler. Karar veya işlem sinyali üretmez.
    """

    rows: list[dict[str, Any]] = []

    for item in records:
        output = _read_output(item)

        rows.append(
            {
                "date": item.get("date"),
                "summary": output.get("summary"),
                "risk_factors": list(output.get("risk_factors", [])),
                "positive_factors": list(
                    output.get("positive_factors", [])
                ),
                "conflicting_points": list(
                    output.get("conflicting_points", [])
                ),
                "watch_items": list(output.get("watch_items", [])),
                "report_count": int(item.get("report_count", 0) or 0),
                "provider": item.get("provider"),
                "model": item.get("model"),
            }
        )

    return rows
