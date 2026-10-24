from types import SimpleNamespace

from backend.app.analysis.morning_priority_view import (
    build_morning_priority_view,
)


def test_priority_view_extracts_actionable_candidates():
    result = build_morning_priority_view(
        (
            SimpleNamespace(
                symbol="TUPRS",
                research_priority="HIGH",
                data_blocked=False,
            ),
            SimpleNamespace(
                symbol="ASELS",
                research_priority="NORMAL",
                data_blocked=False,
            ),
            SimpleNamespace(
                symbol="THYAO",
                research_priority="HIGH",
                data_blocked=True,
            ),
        )
    )

    assert result.total_candidates == 3
    assert result.urgent_count == 1
    assert result.blocked_count == 1
    assert result.top_priority_symbols == ("TUPRS",)
