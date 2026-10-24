from __future__ import annotations

from dataclasses import dataclass

READY_LAST_VALID = "Son geçerli veri kullanılıyor"
REFRESH_REQUIRED = "Yeni veri geldi, yeniden değerlendirme gerekli"
BLOCKED = "Güvenilir veri yok"


@dataclass(frozen=True)
class StatusPolicy:
    status: str
    locked: bool


def evaluate_status_policy(
    *,
    has_data: bool,
    has_previous_valid_data: bool,
    has_new_data: bool,
) -> StatusPolicy:
    if not has_data:
        return StatusPolicy(BLOCKED, True)

    if has_new_data:
        return StatusPolicy(REFRESH_REQUIRED, False)

    if has_previous_valid_data:
        return StatusPolicy(READY_LAST_VALID, False)

    return StatusPolicy(BLOCKED, True)
