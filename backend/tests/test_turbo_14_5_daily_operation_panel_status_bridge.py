from backend.app.analysis.daily_operation_panel_status_bridge import (
    resolve_operation_readiness,
)


def test_ready_last_valid():
    status, locked = resolve_operation_readiness(
        data_state="READY_WITH_LAST_VALID_DATA",
        existing_locked=True,
    )
    assert status == "Son geçerli veri kullanılıyor"
    assert locked is False


def test_refresh_required():
    status, locked = resolve_operation_readiness(
        data_state="REFRESH_REQUIRED",
        existing_locked=False,
    )
    assert status == "Yeni veri geldi, yeniden değerlendirme gerekli"


def test_block():
    status, locked = resolve_operation_readiness(
        data_state="BLOCK",
        existing_locked=True,
    )
    assert status == "Güvenilir veri yok"
    assert locked is True
