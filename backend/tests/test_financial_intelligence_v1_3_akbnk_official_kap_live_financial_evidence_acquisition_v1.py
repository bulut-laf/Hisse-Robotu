import json
from pathlib import Path


def test_akbnk_official_kap_live_financial_evidence_artifact():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_OFFICIAL_KAP_LIVE_FINANCIAL_EVIDENCE_ACQUISITION.json"
    )

    assert path.exists()

    data = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )

    assert data["symbol"] == "AKBNK"
    assert data["notification_id"] == "1637884"
    assert data["source_type"] == "KAP"

    assert data["status"] in {
        "PASS",
        "PASS_FAIL_CLOSED",
    }

    assert data["activation_ready"] is False
    assert data["scoring_ready"] is False
    assert data["store_mutation"] == "NO"
    assert data["al_sat_mutation"] == "NO"

    if data["production_evidence"]:
        assert data["network_fetch"] is True
        assert data["parser_status"] == "PASS"
        assert data["canonical_input_ready"] is True
        assert data["canonical_fact_count"] > 0
        assert data["identity"]["symbol"] == "AKBNK"
        assert str(data["evidence_hash"]).startswith("sha256:")
    else:
        assert data["canonical_input_ready"] is False
        assert len(data["blockers"]) > 0
