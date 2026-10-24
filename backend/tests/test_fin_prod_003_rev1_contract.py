from inspect import signature
from app.analysis import market_multiples
from app.analysis.financial_intelligence_ttm_acceptance import run_ttm_market_acceptance


def test_fin_prod_003_rev1_respects_market_multiples_public_contract():
    params = signature(market_multiples.calculate_market_multiples).parameters
    assert "ebitda_ttm" in params
    assert "fcf_ttm" in params
    assert "earnings_ttm" not in params
    assert "revenue_ttm" not in params
