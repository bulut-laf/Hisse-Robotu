from __future__ import annotations

from typing import Any


def generate_sector_comment(
    sector_report: dict[str, Any],
) -> dict[str, Any]:
    """Sektör raporu için açıklayıcı yorum katmanı.

    AI entegrasyonu için hazırlık katmanıdır.
    İşlem sinyali üretmez.
    """

    sectors = sector_report.get("top_sectors", [])

    comments = []

    for sector in sectors:
        comments.append(
            {
                "sector": sector.get("name"),
                "comment": (
                    "Sektör güçlü görünüm nedeniyle takip "
                    "önceliğine alınabilir. Riskler ayrıca "
                    "değerlendirilmelidir."
                ),
            }
        )

    return {
        "comments": comments,
        "count": len(comments),
    }
