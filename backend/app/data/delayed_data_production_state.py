from __future__ import annotations

from dataclasses import dataclass

READY_LAST_VALID = "Son geçerli veri kullanılıyor"
REFRESH_REQUIRED = "Yeni veri geldi, yeniden değerlendirme gerekli"
BLOCKED = "Güvenilir veri yok"


@dataclass(frozen=True)
class DelayedProductionState:
    status: str
    locked: bool


def resolve_delayed_production_state(
    *,
    has_data: bool,
    has_valid_previous_data: bool,
    has_new_data: bool,
) -> DelayedProductionState:
    if not has_data:
        return DelayedProductionState(BLOCKED, True)

    if has_new_data:
        return DelayedProductionState(REFRESH_REQUIRED, False)

    if has_valid_previous_data:
        return DelayedProductionState(READY_LAST_VALID, False)

    return DelayedProductionState(BLOCKED, True)
