from backend.app.decision_engine.calibration import (
    calibrate_decision_model,
)


def test_calibration_status():
    result = calibrate_decision_model(
        {"success_rate": 0.75}
    )

    assert result["status"] == "stable"


def test_calibration_no_trade_command():
    result = calibrate_decision_model({})

    assert "buy" not in str(result)
    assert "sell" not in str(result)
