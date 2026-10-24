from backend.app.workflow.early_visibility_hardening import (
    harden_early_visibility_operation,
)


def test_ev12_7_operational_hardening():
    result = harden_early_visibility_operation("tuprs")

    assert result.symbol == "TUPRS"
    assert result.status == "READY"
    assert result.source == "EARLY_VISIBILITY"
