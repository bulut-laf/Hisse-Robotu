from backend.app.workflow.production_intelligence_final_lock import (
    build_production_intelligence_final_lock,
)


def test_production_operation_validation():
    result = build_production_intelligence_final_lock("tuprs")

    assert result.intelligence_state == "LOCKED"
    assert result.readiness_state == "READY"
    assert result.source == "EARLY_VISIBILITY"
