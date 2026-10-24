
from pathlib import Path
import json, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "backend/scripts/run_fin_prod_v5_short_term_source_preflight.py"
OUT = ROOT / "backend/data/financial_intelligence/FIN_PROD_V5_SHORT_TERM_SOURCE_PREFLIGHT.json"

def test_contract_markers():
    text = SCRIPT.read_text(encoding="utf-8")
    for marker in (
        "READ_ONLY_SHORT_TERM_SOURCE_PREFLIGHT_V5",
        "No AL/SAT authority.",
        "No scanner/ranking/watchlist mutation.",
        "No portfolio mutation.",
        "No missing metric becomes zero.",
        "historical as_of_date",
        "ensure_ascii=True",
    ):
        assert marker in text

def test_preflight_executes_console_safe():
    p = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "FIN-PROD-V5 PREFLIGHT PASS" in p.stdout
    data = json.loads(OUT.read_text(encoding="utf-8"))
    assert data["status"] == "PASS"
    assert data["schema_version"] == "fin-prod-v5-short-term-source-preflight-v1"
    assert isinstance(data["likely_sources"], list)
