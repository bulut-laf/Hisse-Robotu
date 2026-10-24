from types import SimpleNamespace

from backend.app.analysis.morning_action_board import (
    build_morning_action_board,
)


def test_turbo_04_action_board_creates_daily_actions():
    result = build_morning_action_board(
        (
            SimpleNamespace(symbol="TUPRS", data_blocked=False),
            SimpleNamespace(symbol="ASELS", data_blocked=True),
        )
    )

    assert result.inspect_symbols == ("TUPRS",)
    assert result.blocked_symbols == ("ASELS",)
    assert result.pending_count == 2
    assert result.action_state == "BUGÜNÜN AKSİYONLARI HAZIR"
