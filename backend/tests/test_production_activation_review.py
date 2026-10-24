from backend.app.workflow.production_intelligence_final_lock import (
    build_production_intelligence_final_lock,
)


def test_production_activation_review():
    result = build_production_intelligence_final_lock("tuprs")

    assert result.readiness_state == "READY"
    assert result.source == "EARLY_VISIBILITY"
