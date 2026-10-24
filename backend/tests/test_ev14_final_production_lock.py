from backend.app.workflow.production_intelligence_final_lock import (
    build_production_intelligence_lock,
)


def test_ev14_final_production_lock():
    result = build_production_intelligence_lock("tuprs")

    assert result.symbol == "TUPRS"
    assert result.monitoring_state == "CLOSED"
    assert result.quality_state == "CLOSED"
    assert result.calibration_state == "CLOSED"
    assert result.readiness_state == "READY"
    assert result.source == "EARLY_VISIBILITY"
