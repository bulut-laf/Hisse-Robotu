from backend.app.data.delayed_data_production_state import (
    resolve_delayed_production_state,
    READY_LAST_VALID,
    REFRESH_REQUIRED,
    BLOCKED,
)


def test_ready_last_valid():
    result = resolve_delayed_production_state(
        has_data=True,
        has_valid_previous_data=True,
        has_new_data=False,
    )
    assert result.status == READY_LAST_VALID
    assert result.locked is False


def test_refresh_required():
    result = resolve_delayed_production_state(
        has_data=True,
        has_valid_previous_data=True,
        has_new_data=True,
    )
    assert result.status == REFRESH_REQUIRED


def test_blocked():
    result = resolve_delayed_production_state(
        has_data=False,
        has_valid_previous_data=False,
        has_new_data=False,
    )
    assert result.status == BLOCKED
    assert result.locked is True
