import json
from pathlib import Path


def test_holding_real_data_gate_script_exists():
    root = Path(__file__).resolve().parents[2]

    script = (
        root
        / "backend"
        / "scripts"
        / "run_financial_intelligence_v1_2_"
          "holding_real_data_intake_gate.py"
    )

    assert script.exists()


def test_holding_real_data_gate_contract_if_present():
    root = Path(__file__).resolve().parents[2]

    path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / "FINANCIAL_INTELLIGENCE_V1_2_"
          "HOLDING_REAL_DATA_INTAKE_GATE.json"
    )

    if not path.exists():
        return

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
        data["blockers"],
        list,
    )

    for item in data.get(
        "rejected",
        [],
    ):
        source = str(
            item.get("source")
            or ""
        ).lower()

        assert "_intake_gate" not in source
        assert "_registry" not in source
        assert "_acceptance" not in source

    if data["status"] == "PASS":
        assert (
            data["canonical_input_ready"]
            is True
        )
        assert (
            data["scoring_ready"]
            is True
        )
        assert (
            data["production_evidence"]
            is True
        )
    else:
        assert (
            data["canonical_input_ready"]
            is False
        )
        assert (
            data["scoring_ready"]
            is False
        )
        assert (
            data["production_evidence"]
            is False
        )
