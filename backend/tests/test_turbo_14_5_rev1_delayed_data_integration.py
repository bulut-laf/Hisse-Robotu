from backend.app.data.delayed_data_status_bridge import (
    resolve_delayed_data_decision,
    READY_LAST_VALID,
    REFRESH_REQUIRED,
    BLOCKED,
)


def test_previous_valid_data_ready():
    result = resolve_delayed_data_decision(
        has_valid_previous_data=True,
        has_new_data=False,
        has_data=True,
    )
    assert result.status == READY_LAST_VALID
    assert result.locked is False


def test_new_data_refresh():
    result = resolve_delayed_data_decision(
        has_valid_previous_data=True,
        has_new_data=True,
        has_data=True,
    )
    assert result.status == REFRESH_REQUIRED


def test_missing_data_blocks():
    result = resolve_delayed_data_decision(
        has_valid_previous_data=False,
        has_new_data=False,
        has_data=False,
    )
    assert result.status == BLOCKED
    assert result.locked is True
