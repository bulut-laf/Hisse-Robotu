import json
from pathlib import Path


def test_bank_real_data_gate_excludes_intake_metadata():
    root = Path(__file__).resolve().parents[2]
    gate = root / "backend/data/financial_intelligence/FINANCIAL_INTELLIGENCE_V1_2_BANK_REAL_DATA_INTAKE_GATE.json"

    if not gate.exists():
        return

    data = json.loads(gate.read_text(encoding="utf-8-sig"))

    for item in data.get("rejected", []):
        source = str(item.get("source") or "").lower()
        assert "_new_symbol_intake_gate.json" not in source
