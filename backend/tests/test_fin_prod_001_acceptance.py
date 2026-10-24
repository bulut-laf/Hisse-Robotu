from pathlib import Path

from app.analysis.financial_intelligence_acceptance import run_financial_intelligence_acceptance


def test_fin_prod_acceptance_real_fixture_if_present():
    # Installer creates no fake financial facts. If the real TUPRS fixture is not
    # available in the repository test environment, this acceptance test is skipped.
    candidates = [
        Path("backend/data/TUPRS_1643116_2026_2.xls"),
        Path("backend/tests/fixtures/TUPRS_1643116_2026_2.xls"),
        Path("backend/tests/fixtures/financial_intelligence/TUPRS_1643116_2026_2.xls"),
    ]
    xls = next((p for p in candidates if p.exists()), None)
    if xls is None:
        import pytest
        pytest.skip("real TUPRS KAP fixture not present")

    result = run_financial_intelligence_acceptance(xls)
    assert result["status"] == "PASS"
    assert result["identity"]["symbol"] == "TUPRS"
    assert result["financial_health"]["score"] is not None
    assert result["financial_risk"]["risk_score"] is not None
    assert result["earnings_cash_quality"]["score"] is not None
    assert result["mode"] == "READ_ONLY_PRODUCTION_ACCEPTANCE"
