from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DailyDataState:
    state: str
    message: str
    locked: bool


def evaluate_daily_data_state(
    *,
    has_valid_last_data: bool,
    has_new_data: bool,
    has_any_data: bool,
) -> DailyDataState:
    if not has_any_data:
        return DailyDataState(
            "BLOCK",
            "Güvenilir veri yok",
            True,
        )

    if has_new_data:
        return DailyDataState(
            "REFRESH_REQUIRED",
            "Yeni veri geldi, yeniden değerlendirme gerekli",
            False,
        )

    if has_valid_last_data:
        return DailyDataState(
            "READY_WITH_LAST_VALID_DATA",
            "Son geçerli veri kullanılıyor",
            False,
        )

    return DailyDataState(
        "BLOCK",
        "Geçerli veri bulunamadı",
        True,
    )
