import json
from pathlib import Path


def test_bank_real_source_discovery_artifact_contract():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_REAL_SOURCE_DISCOVERY.json"
    )

    assert path.exists()

    data = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )

    assert data["status"] in {
        "PASS",
        "PASS_FAIL_CLOSED",
    }

    assert data["activation_ready"] is False
    assert data["mutation"] == "NO"
    assert data["store_mutation"] == "NO"
    assert data["al_sat_mutation"] == "NO"

    if data["canonical_candidate_count"] == 0:
        assert (
            "NO_REAL_BANK_CANONICAL_SOURCE_DISCOVERED"
            in data["blockers"]
        )
        assert data["production_evidence"] is False
    else:
        assert data["production_evidence"] is True
        assert data["selected_source"] is not None
