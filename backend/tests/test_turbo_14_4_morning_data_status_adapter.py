from backend.app.analysis.morning_data_status_adapter import build_morning_data_status


def test_ready_status():
    result = build_morning_data_status("READY_WITH_LAST_VALID_DATA")
    assert result.locked is False
    assert result.action == "Mevcut adayları göster"


def test_refresh_status():
    result = build_morning_data_status("REFRESH_REQUIRED")
    assert result.action == "Yeniden değerlendir"


def test_block_status():
    result = build_morning_data_status("BLOCK")
    assert result.locked is True
