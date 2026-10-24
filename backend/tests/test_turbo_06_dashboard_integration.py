from backend.app.analysis.morning_dashboard_integration import (
    build_morning_dashboard_integration,
)


def test_turbo_06_dashboard_integration():
    result = build_morning_dashboard_integration(
        market_state="NORMAL",
        action_count=5,
        priority_count=2,
        inspect_ready_count=4,
    )

    assert result.market_state == "NORMAL"
    assert result.action_count == 5
    assert result.priority_count == 2
    assert result.inspect_ready_count == 4
    assert result.integration_state == "DASHBOARD ENTEGRASYONU HAZIR"
