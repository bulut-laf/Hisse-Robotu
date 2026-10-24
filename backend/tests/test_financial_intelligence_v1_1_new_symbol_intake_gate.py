import json
import subprocess
from pathlib import Path


def test_intake_gate_blocks_missing_source_and_nonindustrial_without_dedicated_model(tmp_path):
    root = Path(__file__).resolve().parents[2]
    py = root / ".venv/Scripts/python.exe"
    script = root / "backend/scripts/run_financial_intelligence_v1_1_new_symbol_intake_gate.py"

    cp = subprocess.run(
        [
            str(py), str(script),
            "--project-root", str(root),
            "--symbol", "ISCTR",
            "--sector-model", "BANK",
            "--source-file", str(tmp_path / "missing.xls"),
            "--period", "2026_2",
        ],
        capture_output=True, text=True, check=True,
    )
    assert "STATUS=BLOCKED" in cp.stdout

    out = root / "backend/data/financial_intelligence/ISCTR_new_symbol_intake_gate.json"
    data = json.loads(out.read_text(encoding="utf-8-sig"))
    assert "SOURCE_FILE_MISSING" in data["blockers"]
    assert "DEDICATED_BANK_MODEL_REQUIRED" in data["blockers"]
    assert data["next_stage"] is None


def test_intake_gate_allows_real_industrial_source(tmp_path):
    root = Path(__file__).resolve().parents[2]
    py = root / ".venv/Scripts/python.exe"
    script = root / "backend/scripts/run_financial_intelligence_v1_1_new_symbol_intake_gate.py"

    src = tmp_path / "KRDMD_2026_2.xls"
    src.write_bytes(b"real-source-placeholder-for-contract-test")

    cp = subprocess.run(
        [
            str(py), str(script),
            "--project-root", str(root),
            "--symbol", "KRDMD",
            "--sector-model", "INDUSTRIAL",
            "--source-file", str(src),
            "--period", "2026_2",
        ],
        capture_output=True, text=True, check=True,
    )
    assert "STATUS=READY_FOR_CANONICAL_ACCEPTANCE_IMPORT" in cp.stdout

    out = root / "backend/data/financial_intelligence/KRDMD_new_symbol_intake_gate.json"
    data = json.loads(out.read_text(encoding="utf-8-sig"))
    assert data["blockers"] == []
    assert data["next_stage"] == "FIN001_CANONICAL_ACCEPTANCE_IMPORT"
