from backend.app.data.turbo_14_9_status_policy import evaluate_status_policy


def test_last_valid_data():
    result = evaluate_status_policy(
        has_data=True,
        has_previous_valid_data=True,
        has_new_data=False,
    )
    assert result.locked is False


def test_new_data_refresh():
    result = evaluate_status_policy(
        has_data=True,
        has_previous_valid_data=True,
        has_new_data=True,
    )
    assert "yeniden değerlendirme" in result.status


def test_no_data_block():
    result = evaluate_status_policy(
        has_data=False,
        has_previous_valid_data=False,
        has_new_data=False,
    )
    assert result.locked is True
