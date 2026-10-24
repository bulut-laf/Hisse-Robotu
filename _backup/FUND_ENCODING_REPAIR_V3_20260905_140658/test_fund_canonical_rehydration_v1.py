from pathlib import Path
from backend.app.funds.analysis_engine import FundAnalysisClass, FundAnalysisResult
from backend.app.funds.canonical_result_store import load_last_good_fund_analysis_results, save_last_good_fund_analysis_results
from backend.app.funds.ui_live_refresh import refresh_fund_analysis_if_requested

def _result(code="AP5"):
    return FundAnalysisResult(canonical_fund_id=f"fund:tefas:{code}", category_id=None, classification=FundAnalysisClass.X, class_label="X", positive_families=(), neutral_families=(), caution_families=(), unavailable_families=("F1",), eligibility_reason="INSUFFICIENT_INDEPENDENT_EVIDENCE", explanation="test")

def test_empty_refresh_preserves_last_good():
    current = (_result(),)
    outcome = refresh_fund_analysis_if_requested(requested=True, current_results=current, loader=lambda: ())
    assert outcome.results == current
    assert outcome.refreshed is False
    assert outcome.error_message == "TEFAS_EMPTY_RESULT"

def test_snapshot_roundtrip(tmp_path: Path):
    path = tmp_path / "canonical.json"
    original = (_result("AP5"), _result("AAL"))
    assert save_last_good_fund_analysis_results(original, path=path) == 2
    loaded = load_last_good_fund_analysis_results(path=path)
    assert [x.canonical_fund_id for x in loaded] == ["fund:tefas:AP5", "fund:tefas:AAL"]
