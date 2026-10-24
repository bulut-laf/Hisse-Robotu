from backend.app.analysis.daily_operation_data_bridge import build_operation_data_view


def test_ready_with_last_valid_data():
    result = build_operation_data_view(
        daily_data_state="READY_WITH_LAST_VALID_DATA"
    )
    assert result.state == "READY"
    assert result.locked is False


def test_refresh_required():
    result = build_operation_data_view(
        daily_data_state="REFRESH_REQUIRED"
    )
    assert result.state == "REFRESH_REQUIRED"


def test_block_when_no_data():
    result = build_operation_data_view(
        daily_data_state="BLOCK"
    )
    assert result.locked is True
