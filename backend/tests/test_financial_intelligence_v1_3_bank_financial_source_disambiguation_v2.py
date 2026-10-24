import json
from pathlib import Path


def test_bank_financial_source_disambiguation_v2_contract():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_FINANCIAL_SOURCE_DISAMBIGUATION_V2.json"
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

    assert (
        data["canonical_producer_ready"]
        is False
    )
    assert (
        data["production_evidence"]
        is False
    )
    assert (
        data["activation_ready"]
        is False
    )

    for row in data[
        "top_candidates"
    ]:
        path_text = row[
            "path"
        ].lower()

        assert "free_float" not in path_text
        assert "\\\\_backup\\\\" not in path_text

    if data[
        "credible_candidate_count"
    ] == 0:
        assert (
            "NO_REAL_BANK_FINANCIAL_SOURCE"
            in data["blockers"]
        )

    assert data["mutation"] == "NO"
    assert data["store_mutation"] == "NO"
    assert data["al_sat_mutation"] == "NO"
