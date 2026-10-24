from __future__ import annotations

from dataclasses import dataclass


SON_GECERLI_VERI = "Son geçerli veri kullanılıyor"
YENIDEN_DEGERLENDIR = "Yeni veri geldi, yeniden değerlendirme gerekli"
VERI_YOK = "Güvenilir veri yok"


@dataclass(frozen=True)
class DelayedStatusDecision:
    status: str
    locked: bool
    preview_only: bool


def resolve_status_for_state(
    *,
    has_data: bool,
    has_previous_valid_data: bool,
    has_new_data: bool,
) -> DelayedStatusDecision:
    if not has_data:
        return DelayedStatusDecision(
            VERI_YOK,
            True,
            False,
        )

    if has_new_data:
        return DelayedStatusDecision(
            YENIDEN_DEGERLENDIR,
            False,
            False,
        )

    if has_previous_valid_data:
        return DelayedStatusDecision(
            SON_GECERLI_VERI,
            False,
            False,
        )

    return DelayedStatusDecision(
        VERI_YOK,
        True,
        False,
    )
