import json
from pathlib import Path


def test_bank_raw_source_schema_characterization_artifact():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_BANK_RAW_SOURCE_SCHEMA_CHARACTERIZATION.json"
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

    assert isinstance(
        data["bank_record_count"],
        int,
    )

    assert isinstance(
        data["unique_source_file_count"],
        int,
    )

    assert isinstance(
        data["top_candidates"],
        list,
    )

    assert (
        data["canonical_producer_ready"]
        is False
    )

    assert data["mutation"] == "NO"
    assert data["store_mutation"] == "NO"
    assert data["al_sat_mutation"] == "NO"
