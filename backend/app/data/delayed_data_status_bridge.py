from __future__ import annotations

from dataclasses import dataclass


READY_LAST_VALID = "Son geçerli veri kullanılıyor"
REFRESH_REQUIRED = "Yeni veri geldi, yeniden değerlendirme gerekli"
BLOCKED = "Güvenilir veri yok"


@dataclass(frozen=True)
class DelayedDataDecision:
    status: str
    locked: bool


def resolve_delayed_data_decision(
    *,
    has_valid_previous_data: bool,
    has_new_data: bool,
    has_data: bool,
) -> DelayedDataDecision:
    if not has_data:
        return DelayedDataDecision(BLOCKED, True)

    if has_new_data:
        return DelayedDataDecision(REFRESH_REQUIRED, False)

    if has_valid_previous_data:
        return DelayedDataDecision(READY_LAST_VALID, False)

    return DelayedDataDecision(BLOCKED, True)
