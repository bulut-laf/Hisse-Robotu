import json
from pathlib import Path


def test_bank_canonical_exact_shape_diagnostic():
    root = Path(__file__).resolve().parents[2]
    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_CANONICAL_EXACT_SHAPE_DIAGNOSTIC.json"
    )

    assert path.exists()

    data = json.loads(path.read_text(encoding="utf-8-sig"))

    assert data["status"] in {"PASS", "PASS_FAIL_CLOSED"}
    assert data["production_mutation"] == "NO"
    assert data["store_mutation"] == "NO"
    assert data["al_sat_mutation"] == "NO"

    if data["canonical_shape_ready"]:
        assert data["component_metric_map"]
        assert data["blocker_sites"]
        assert any(
            path.endswith(".capital_adequacy_ratio")
            for path in data["required_metric_paths"]
        )
    else:
        assert data["blockers"]
