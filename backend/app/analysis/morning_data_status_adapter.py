from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MorningDataStatus:
    label: str
    locked: bool
    action: str


def build_morning_data_status(state: str) -> MorningDataStatus:
    if state == "READY_WITH_LAST_VALID_DATA":
        return MorningDataStatus(
            label="Son geçerli veri kullanılıyor",
            locked=False,
            action="Mevcut adayları göster",
        )

    if state == "REFRESH_REQUIRED":
        return MorningDataStatus(
            label="Yeni veri geldi, yeniden değerlendirme gerekli",
            locked=False,
            action="Yeniden değerlendir",
        )

    return MorningDataStatus(
        label="Güvenilir veri yok",
        locked=True,
        action="Analizi durdur",
    )
