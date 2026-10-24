from __future__ import annotations

from dataclasses import dataclass

READY_LAST_VALID = "Son geçerli veri kullanılıyor"
REFRESH_REQUIRED = "Yeni veri geldi, yeniden değerlendirme gerekli"
BLOCKED = "Güvenilir veri yok"


@dataclass(frozen=True)
class StatusForResult:
    status: str
    locked: bool
    preview_only: bool


def resolve_status_for(
    *,
    has_data: bool,
    has_valid_previous_data: bool,
    has_new_data: bool,
) -> StatusForResult:
    if not has_data:
        return StatusForResult(BLOCKED, True, False)

    if has_new_data:
        return StatusForResult(REFRESH_REQUIRED, False, False)

    if has_valid_previous_data:
        return StatusForResult(READY_LAST_VALID, False, False)

    return StatusForResult(BLOCKED, True, False)
