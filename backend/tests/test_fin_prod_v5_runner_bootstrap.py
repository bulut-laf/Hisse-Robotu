
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "backend" / "scripts" / "run_fin_prod_v5_short_term_context.py"


def test_v5_runner_bootstraps_project_root_for_direct_execution():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "PROJECT_ROOT = Path(__file__).resolve().parents[2]" in text
    assert "sys.path.insert(0, str(PROJECT_ROOT))" in text


def test_v5_runner_direct_help_imports_backend_package():
    p = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr
    assert "--as-of-date" in p.stdout
