from backend.app.data.status_for_production_adapter import (
    resolve_status_for,
    READY_LAST_VALID,
    REFRESH_REQUIRED,
    BLOCKED,
)


def test_ready_last_valid():
    result = resolve_status_for(
        has_data=True,
        has_valid_previous_data=True,
        has_new_data=False,
    )
    assert result.status == READY_LAST_VALID
    assert result.locked is False


def test_refresh_required():
    result = resolve_status_for(
        has_data=True,
        has_valid_previous_data=True,
        has_new_data=True,
    )
    assert result.status == REFRESH_REQUIRED


def test_blocked():
    result = resolve_status_for(
        has_data=False,
        has_valid_previous_data=False,
        has_new_data=False,
    )
    assert result.status == BLOCKED
    assert result.locked is True
