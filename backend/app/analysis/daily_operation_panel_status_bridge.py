from __future__ import annotations


def resolve_operation_readiness(
    *,
    data_state: str,
    existing_locked: bool,
) -> tuple[str, bool]:
    if data_state == "READY_WITH_LAST_VALID_DATA":
        return "Son geçerli veri kullanılıyor", False

    if data_state == "REFRESH_REQUIRED":
        return "Yeni veri geldi, yeniden değerlendirme gerekli", False

    return ("Güvenilir veri yok", True if existing_locked else True)
