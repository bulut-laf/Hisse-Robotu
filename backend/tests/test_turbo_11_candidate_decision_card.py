from types import SimpleNamespace

from backend.app.analysis.candidate_decision_card import (
    build_candidate_decision_card,
)


def test_turbo_11_candidate_decision_card():
    result = build_candidate_decision_card(
        SimpleNamespace(
            symbol="tuprs",
            reasons=("Early Visibility", "Teknik bağlam"),
            risks=("Teyit ihtiyacı",),
        )
    )

    assert result.symbol == "TUPRS"
    assert result.reasons == ("Early Visibility", "Teknik bağlam")
    assert result.risks == ("Teyit ihtiyacı",)
    assert result.next_module == "GÜNCEL TEKNİK ANALİZ"
