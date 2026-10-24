from backend.app.data.valid_daily_data_state import evaluate_daily_data_state


def test_last_valid_data_is_ready():
    result = evaluate_daily_data_state(
        has_valid_last_data=True,
        has_new_data=False,
        has_any_data=True,
    )
    assert result.state == "READY_WITH_LAST_VALID_DATA"
    assert result.locked is False


def test_new_data_requests_refresh():
    result = evaluate_daily_data_state(
        has_valid_last_data=True,
        has_new_data=True,
        has_any_data=True,
    )
    assert result.state == "REFRESH_REQUIRED"


def test_no_data_blocks():
    result = evaluate_daily_data_state(
        has_valid_last_data=False,
        has_new_data=False,
        has_any_data=False,
    )
    assert result.state == "BLOCK"
    assert result.locked is True
