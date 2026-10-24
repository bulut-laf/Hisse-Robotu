from app.analysis.financial_intelligence_sector_model_registry import (
    PRODUCTION_READY_MODELS, SUPPORTED_SECTOR_MODELS, resolve_sector_model_route,
)
def main():
    print(f"SUPPORTED_SECTOR_MODELS={list(SUPPORTED_SECTOR_MODELS)}")
    print(f"PRODUCTION_READY_MODELS={list(PRODUCTION_READY_MODELS)}")
    for model in SUPPORTED_SECTOR_MODELS:
        route = resolve_sector_model_route(model)
        print(f"{model}:STATUS={route.status};READY={route.production_ready};BLOCKER={route.blocker}")
    assert resolve_sector_model_route("INDUSTRIAL").status == "PASS"
    for model in ("BANK","INSURANCE","REIT","HOLDING"):
        route = resolve_sector_model_route(model)
        assert route.status == "BLOCKED" and not route.production_ready
    print("FINANCIAL_INTELLIGENCE_V1_2_SECTOR_MODEL_REGISTRY_ROUTING_V1=PASS")
if __name__ == "__main__":
    main()
