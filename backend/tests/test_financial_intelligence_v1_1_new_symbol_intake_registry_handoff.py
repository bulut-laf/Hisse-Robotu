import json
from pathlib import Path


def test_intake_registry_handoff_contract():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_1_NEW_SYMBOL_INTAKE_REGISTRY_HANDOFF.json"
    assert p.exists()

    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["status"] in {
        "PASS_NO_INTAKE_ARTIFACT",
        "PASS_ALREADY_REGISTERED",
        "PASS_WAITING_FOR_CANONICAL_PANEL",
        "PASS_READY_FOR_REGISTRY_REFRESH",
        "BLOCKED",
    }

    assert "registry_updated" in data
    assert "blockers" in data
    assert "registry_artifact" in data


def test_handoff_never_mutates_registry_directly():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_1_NEW_SYMBOL_INTAKE_REGISTRY_HANDOFF.json"
    data = json.loads(p.read_text(encoding="utf-8-sig"))

    assert data["registry_updated"] is False
