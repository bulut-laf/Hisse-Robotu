from backend.app.operations.valid_data_state import evaluate_valid_data_state

def test_last_valid_data():
    assert evaluate_valid_data_state(True, False, True).state == "READY_WITH_LAST_VALID_DATA"

def test_refresh():
    assert evaluate_valid_data_state(True, True, True).state == "REFRESH_REQUIRED"

def test_block():
    assert evaluate_valid_data_state(False, False, False).state == "BLOCK"
