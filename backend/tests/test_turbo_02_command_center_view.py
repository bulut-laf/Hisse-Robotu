from backend.app.analysis.morning_command_center_view import (
    build_morning_command_center_view,
)


def test_turbo_02_command_center_view():
    result = build_morning_command_center_view(
        market_state="NORMAL",
        candidates=(object(), object(), object()),
        priority_symbols=("TUPRS", "ASELS"),
        pending_actions=3,
    )

    assert result.market_state == "NORMAL"
    assert result.candidate_count == 3
    assert result.priority_symbols == ("TUPRS", "ASELS")
    assert result.pending_actions == 3
    assert result.view_state == "SABAH OPERASYON MERKEZİ HAZIR"
