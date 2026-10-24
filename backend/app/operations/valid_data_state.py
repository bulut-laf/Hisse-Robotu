from dataclasses import dataclass

@dataclass(frozen=True)
class ValidDataState:
    state: str
    message: str

def evaluate_valid_data_state(has_last_successful_scan, has_new_data, data_available):
    if not data_available:
        return ValidDataState("BLOCK", "Güvenilir veri yok")
    if has_new_data:
        return ValidDataState("REFRESH_REQUIRED", "Yeni veri geldi")
    if has_last_successful_scan:
        return ValidDataState("READY_WITH_LAST_VALID_DATA", "Son geçerli veri kullanılıyor")
    return ValidDataState("BLOCK", "Geçerli tarama yok")
