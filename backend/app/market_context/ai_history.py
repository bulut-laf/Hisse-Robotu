from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AIEvaluationHistory:
    """Geçmiş AI değerlendirmelerini tutar.

    Karar üretmez.
    Sadece tarihsel değerlendirme kayıtlarını saklar.
    """

    evaluations: list[dict[str, Any]] = field(default_factory=list)

    def add(self, evaluation: dict[str, Any]) -> None:
        self.evaluations.append(evaluation)

    def count(self) -> int:
        return len(self.evaluations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_count": self.count(),
            "evaluations": list(self.evaluations),
        }


def load_ai_evaluation_history(
    data_root: str | Path,
    *,
    limit: int = 7,
) -> list[dict[str, Any]]:
    """Sprint-139C AI arşivinden son değerlendirmeleri okur.

    Aynı gün birden fazla kayıt varsa en son oluşturulan kayıt kullanılır.
    Sonuç tarih sırasıyla eskiden yeniye döner.
    """

    root = Path(data_root) / "market_context_ai_evaluations"
    if not root.exists():
        return []

    records: list[dict[str, Any]] = []

    for path in root.glob("*/*.json"):
        if not path.is_file():
            continue

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if (
            isinstance(payload, dict)
            and str(payload.get("date", "")).strip()
            and isinstance(payload.get("output"), dict)
        ):
            records.append(payload)

    latest_by_date: dict[str, dict[str, Any]] = {}

    for record in records:
        record_date = str(record.get("date"))
        current = latest_by_date.get(record_date)

        if current is None:
            latest_by_date[record_date] = record
            continue

        if str(record.get("created_at", "")) >= str(
            current.get("created_at", "")
        ):
            latest_by_date[record_date] = record

    ordered = [
        latest_by_date[key]
        for key in sorted(latest_by_date)
    ]

    safe_limit = max(1, int(limit))
    return ordered[-safe_limit:]
