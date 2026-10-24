from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AIPromptContract:
    """AI değerlendirme talimat sözleşmesi.

    Gerçek AI çağrısı yapmaz.
    Tutarlı değerlendirme formatı için kural seti taşır.
    """

    role: str = "Piyasa analisti destek asistanı"
    scope: str = "Market context analysis only"

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "scope": self.scope,
        }
