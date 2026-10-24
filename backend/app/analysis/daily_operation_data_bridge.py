from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OperationDataView:
    state: str
    message: str
    locked: bool


def build_operation_data_view(
    *,
    daily_data_state: str,
) -> OperationDataView:
    if daily_data_state == "READY_WITH_LAST_VALID_DATA":
        return OperationDataView(
            state="READY",
            message="Son geçerli veri kullanılıyor",
            locked=False,
        )

    if daily_data_state == "REFRESH_REQUIRED":
        return OperationDataView(
            state="REFRESH_REQUIRED",
            message="Yeni veri geldi, yeniden değerlendirme gerekli",
            locked=False,
        )

    return OperationDataView(
        state="BLOCK",
        message="Güvenilir veri yok",
        locked=True,
    )
