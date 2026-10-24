from backend.app.analysis.morning_user_dashboard import (
    build_morning_user_dashboard,
)


def test_turbo_05_user_dashboard():
    result = build_morning_user_dashboard(
        market_state="NORMAL",
        action_count=5,
        priority_count=2,
        inspect_ready=4,
    )

    assert result.market_state == "NORMAL"
    assert result.action_count == 5
    assert result.priority_count == 2
    assert result.inspect_ready == 4
    assert result.dashboard_state == "SABAH KULLANICI PANELİ HAZIR"
