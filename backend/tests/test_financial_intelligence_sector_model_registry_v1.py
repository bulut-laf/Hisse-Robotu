import pytest
from app.analysis.financial_intelligence_sector_model_registry import (
    PRODUCTION_READY_MODELS, SUPPORTED_SECTOR_MODELS,
    assert_sector_model_production_ready, resolve_sector_model_route,
)

def test_registry_contract():
    assert SUPPORTED_SECTOR_MODELS == ("INDUSTRIAL","BANK","INSURANCE","REIT","HOLDING")
    assert PRODUCTION_READY_MODELS == ("INDUSTRIAL",)

def test_industrial_routes_production_ready():
    route = resolve_sector_model_route(" industrial ")
    assert route.status == "PASS"
    assert route.resolved_model == "INDUSTRIAL"
    assert route.production_ready is True
    assert route.blocker is None
    assert assert_sector_model_production_ready("INDUSTRIAL") == "INDUSTRIAL"

@pytest.mark.parametrize("model,blocker", [
    ("BANK","DEDICATED_BANK_MODEL_REQUIRED"),
    ("INSURANCE","DEDICATED_INSURANCE_MODEL_REQUIRED"),
    ("REIT","DEDICATED_REIT_MODEL_REQUIRED"),
    ("HOLDING","DEDICATED_HOLDING_MODEL_REQUIRED"),
])
def test_nonindustrial_models_fail_closed(model, blocker):
    route = resolve_sector_model_route(model)
    assert route.status == "BLOCKED"
    assert route.resolved_model == model
    assert route.production_ready is False
    assert route.blocker == blocker
    with pytest.raises(ValueError, match=blocker):
        assert_sector_model_production_ready(model)

def test_missing_and_unknown_fail_closed():
    missing = resolve_sector_model_route(None)
    assert missing.status == "BLOCKED"
    assert missing.blocker == "SECTOR_MODEL_MISSING"
    unknown = resolve_sector_model_route("UTILITY")
    assert unknown.status == "BLOCKED"
    assert unknown.blocker == "SECTOR_MODEL_UNSUPPORTED:UTILITY"
