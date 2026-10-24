from __future__ import annotations

from typing import Any


def build_sector_opportunity_view(
    sectors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sektör fırsat görünümü için sıralı veri hazırlar."""

    return sorted(
        sectors,
        key=lambda item: item.get("strength_score", 0),
        reverse=True,
    )
