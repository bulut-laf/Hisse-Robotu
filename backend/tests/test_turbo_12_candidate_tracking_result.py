from types import SimpleNamespace

from backend.app.analysis.candidate_tracking_result import (
    build_candidate_tracking_result,
)


def test_turbo_12_candidate_tracking_result():
    result = build_candidate_tracking_result(
        SimpleNamespace(
            symbol="tuprs",
            tracking_state="TAKİPTE",
            result_state="BEKLEMEDE",
        )
    )

    assert result.symbol == "TUPRS"
    assert result.tracking_state == "TAKİPTE"
    assert result.result_state == "BEKLEMEDE"
    assert result.next_step == "GÜN SONU DEĞERLENDİRME"
