import json
from pathlib import Path


def test_official_kap_bank_financial_acquisition_contract():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_3_OFFICIAL_KAP_BANK_FINANCIAL_ACQUISITION_CONTRACT.json"
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
        data["production_evidence"]
        is False
    )
    assert (
        data["bank_activation_ready"]
        is False
    )

    assert data["mutation"] == "NO"
    assert data["store_mutation"] == "NO"
    assert data["al_sat_mutation"] == "NO"

    if data["status"] == "PASS":
        assert (
            data["required_present"][
                "kap_flow_rows"
            ]
            is True
        )
        assert (
            data["required_present"][
                "import_kap_financial_xls_bytes"
            ]
            is True
        )
        assert len(
            data["endpoint_lines"]
        ) > 0
        assert (
            data["live_acquisition_ready"]
            is True
        )
