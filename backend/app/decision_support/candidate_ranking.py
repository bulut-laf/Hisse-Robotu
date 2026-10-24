from __future__ import annotations

from typing import Any


def rank_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Birleşik adayları öncelik skoruna göre sıralar.

    Karar desteği sağlar.
    Doğrudan işlem emri üretmez.
    """

    return sorted(
        candidates,
        key=lambda item: item.get("score", 0),
        reverse=True,
    )
