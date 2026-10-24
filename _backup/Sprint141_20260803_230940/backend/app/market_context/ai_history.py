from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIEvaluationHistory:
    """Geçmiş AI değerlendirmelerini karşılaştırma hazırlığı.

    Karar üretmez.
    Sadece tarihsel değerlendirme kayıtlarını tutar.
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
