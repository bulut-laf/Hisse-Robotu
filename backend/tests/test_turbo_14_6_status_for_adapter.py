from backend.app.data.delayed_status_for_adapter import (
    resolve_status_for_state,
    SON_GECERLI_VERI,
    YENIDEN_DEGERLENDIR,
    VERI_YOK,
)


def test_last_valid_data():
    result = resolve_status_for_state(
        has_data=True,
        has_previous_valid_data=True,
        has_new_data=False,
    )
    assert result.status == SON_GECERLI_VERI
    assert result.locked is False


def test_new_data():
    result = resolve_status_for_state(
        has_data=True,
        has_previous_valid_data=True,
        has_new_data=True,
    )
    assert result.status == YENIDEN_DEGERLENDIR


def test_no_data():
    result = resolve_status_for_state(
        has_data=False,
        has_previous_valid_data=False,
        has_new_data=False,
    )
    assert result.status == VERI_YOK
    assert result.locked is True
