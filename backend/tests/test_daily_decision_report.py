from backend.app.decision_engine.daily_decision_report import (
    build_daily_decision_report,
)


def test_daily_report():
    result = build_daily_decision_report(
        [
            {"symbol": "AKBNK", "decision": "AL ADAYI"}
        ],
        [
            {"symbol": "THYAO", "decision": "TUT"}
        ],
    )

    assert result["candidate_count"] == 1
    assert result["position_count"] == 1


def test_daily_report_no_trade_command():
    result = build_daily_decision_report([], [])

    assert "buy" not in str(result).lower()
    assert "sell" not in str(result).lower()
