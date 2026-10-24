from __future__ import annotations

from dataclasses import dataclass
from typing import Any


OUTPUT_FIELDS = (
    "summary",
    "positive_factors",
    "risk_factors",
    "aligned_points",
    "conflicting_points",
    "watch_items",
)


@dataclass(slots=True)
class AIPromptContract:
    """AI değerlendirme talimat sözleşmesi.

    Gerçek AI çağrısı yapmaz.
    Sağlayıcıya verilecek rol, kapsam, güvenlik ve çıktı kurallarını
    standartlaştırır.
    """

    role: str = "Piyasa analisti destek asistanı"
    scope: str = "Market context analysis only"
    language: str = "Türkçe"

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "scope": self.scope,
            "language": self.language,
            "evidence_policy": (
                "Yalnızca sağlanan günlük piyasa bağlamı ve rapor içeriklerine dayan. "
                "Kaynaklarda bulunmayan veri, olay, fiyat, tarih veya gerekçe uydurma."
            ),
            "uncertainty_policy": (
                "Bilgi yetersiz veya belirsizse bunu açıkça belirt; kesinlik üretme."
            ),
            "conflict_policy": (
                "Kaynaklar arasında çelişki varsa bunu conflicting_points alanında belirt."
            ),
            "safety_policy": (
                "Al/sat talimatı, yatırım tavsiyesi, hedef fiyat, stop seviyesi, "
                "pozisyon açma-kapama önerisi veya teknik skor üretme."
            ),
            "output_fields": list(OUTPUT_FIELDS),
        }
