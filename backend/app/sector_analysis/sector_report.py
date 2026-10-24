from __future__ import annotations

from typing import Any


def build_sector_report(
    sectors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Sektör karar destek raporu oluşturur.

    Yalnızca sektör bağlamı üretir.
    İşlem sinyali üretmez.
    """

    ranked = sorted(
        sectors,
        key=lambda item: item.get("score", 0),
        reverse=True,
    )

    return {
        "top_sectors": ranked[:3],
        "sector_count": len(ranked),
    }
