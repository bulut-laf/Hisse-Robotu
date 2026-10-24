from backend.app.decision_engine.scan_decision_bridge import (
    attach_decision_to_scan,
)


def test_scan_decision_bridge():
    result = attach_decision_to_scan(
        [
            {
                "symbol": "AKBNK",
                "decision_label": "AL ADAYI",
            }
        ]
    )

    assert result[0]["symbol"] == "AKBNK"
    assert result[0]["decision_ready"] is True


def test_scan_decision_bridge_no_trade_command():
    result = attach_decision_to_scan([])

    assert "buy" not in str(result).lower()
    assert "sell" not in str(result).lower()
