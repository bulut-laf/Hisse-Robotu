from pathlib import Path

DASHBOARD = Path("backend/dashboard.py")

def _fund_block() -> str:
    text = DASHBOARD.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == 'elif analiz_modu == "Fon Analiz Merkezi":')
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("    elif analiz_modu == ")), len(lines))
    return "\n".join(lines[start:end])

def test_rehydration_is_wired_into_exact_fund_route():
    block = _fund_block()
    assert "load_last_good_fund_analysis_results" in block
    assert "fund_analysis_rehydrated_from_snapshot" in block
    assert "st.session_state[live_results_key] = rehydrated_results" in block

def test_successful_refresh_is_persisted():
    block = _fund_block()
    assert "save_last_good_fund_analysis_results(refresh_outcome.results)" in block
