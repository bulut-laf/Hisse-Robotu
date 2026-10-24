from backend.app.decision_engine.scan_integration import (
    integrate_scan_candidates,
)


def test_scan_integration():
    result = integrate_scan_candidates(
        [
            {
                "symbol": "AKBNK",
                "sector": "Bankacılık",
                "score": 85,
            }
        ]
    )

    assert result[0]["symbol"] == "AKBNK"
    assert result[0]["decision_ready"] is True


def test_scan_integration_no_trade_command():
    result = integrate_scan_candidates([])

    assert "buy" not in str(result)
    assert "sell" not in str(result)
