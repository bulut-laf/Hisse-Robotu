from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class MorningOperationReview:
    total_candidates: int
    reviewed_candidates: int
    pending_candidates: int
    review_state: str


def build_morning_operation_review(
    feedback_items: Iterable[object],
) -> MorningOperationReview:
    items = tuple(feedback_items)

    reviewed = sum(
        str(getattr(item, "user_state", "")).casefold()
        in {"incelendi", "işlem yapıldı", "pas geçildi"}
        for item in items
    )

    return MorningOperationReview(
        total_candidates=len(items),
        reviewed_candidates=reviewed,
        pending_candidates=len(items) - reviewed,
        review_state=(
            "GERİ BİLDİRİM TAMAMLANDI"
            if len(items) > 0 and reviewed == len(items)
            else "GERİ BİLDİRİM BEKLİYOR"
        ),
    )
