from __future__ import annotations

from typing import Any


def rank_sectors(
    sectors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sektörleri güç skoruna göre sıralar.

    Sadece sektör önceliklendirmesi yapar.
    İşlem sinyali üretmez.
    """

    return sorted(
        sectors,
        key=lambda item: item.get("score", 0),
        reverse=True,
    )
