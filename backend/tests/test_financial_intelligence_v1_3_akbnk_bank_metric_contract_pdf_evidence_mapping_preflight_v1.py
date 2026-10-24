import json
from pathlib import Path


def test_akbnk_bank_metric_contract_pdf_mapping_preflight():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_BANK_METRIC_CONTRACT_PDF_EVIDENCE_MAPPING_PREFLIGHT.json"
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
        data["numeric_mapping_ready"]
        is False
    )

    assert (
        data["scoring_ready"]
        is False
    )

    assert (
        data["activation_ready"]
        is False
    )

    assert (
        data["production_mutation"]
        == "NO"
    )

    assert (
        data["store_mutation"]
        == "NO"
    )

    assert (
        data["al_sat_mutation"]
        == "NO"
    )

    if data[
        "mapping_preflight_ready"
    ]:
        assert (
            data[
                "metric_candidate_count"
            ]
            > 0
        )
        assert (
            data[
                "metric_with_evidence_count"
            ]
            > 0
        )
        assert isinstance(
            data[
                "metric_evidence"
            ],
            dict,
        )
    else:
        assert len(
            data["blockers"]
        ) > 0
