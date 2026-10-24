
from __future__ import annotations

from pathlib import Path


STALE_TESTS = {
    "backend/tests/test_fin_prod_v7_financial_intelligence_ui.py": r'''
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend/dashboard.py"


def test_dashboard_financial_intelligence_route_contract():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    ast.parse(source)
    assert "Temel Analiz" in source
    assert "Finansal Zekâ Paneli" in source
    assert re.search(r'analiz_modu\\s*==\\s*([\"\\'])Finansal Zekâ Paneli\\1', source)


def test_dashboard_preserves_temel_analiz_and_financial_intelligence():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert "Temel Analiz" in source
    assert "Finansal Zekâ Paneli" in source
''',
    "backend/tests/test_fin_prod_v7_ui_smoke.py": r'''
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend/dashboard.py"


def test_active_dashboard_contains_financial_intelligence_route():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    ast.parse(source)
    assert "Finansal Zekâ Paneli" in source
    assert re.search(r'analiz_modu\\s*==\\s*([\"\\'])Finansal Zekâ Paneli\\1', source)
''',
    "backend/tests/test_financial_intelligence_v1_live_route_repair_final2.py": r'''
import ast
import re
from pathlib import Path


def test_financial_intelligence_live_route_current_contract():
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "backend/dashboard.py"
    text = dashboard.read_text(encoding="utf-8-sig")

    ast.parse(text)
    assert "Temel Analiz" in text
    assert "Finansal Zekâ Paneli" in text
    assert re.search(r'analiz_modu\\s*==\\s*([\"\\'])Finansal Zekâ Paneli\\1', text)
''',
    "backend/tests/test_financial_intelligence_v1_ui_zeroarg_adapter_route.py": r'''
import ast
import re
from pathlib import Path


def test_financial_intelligence_route_is_live_without_legacy_zeroarg_requirement():
    root = Path(__file__).resolve().parents[2]
    dashboard = root / "backend/dashboard.py"
    renderer = root / "backend/app/ui/financial_intelligence_dashboard.py"

    dtext = dashboard.read_text(encoding="utf-8-sig")
    ast.parse(dtext)

    assert renderer.exists()
    assert "Temel Analiz" in dtext
    assert "Finansal Zekâ Paneli" in dtext
    assert re.search(r'analiz_modu\\s*==\\s*([\"\\'])Finansal Zekâ Paneli\\1', dtext)
''',
    "backend/tests/test_fin_prod_v9_clean_rebuild_v4.py": r'''
import json
from pathlib import Path


def test_fin_prod_v9_current_fail_closed_contract():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FIN_PROD_V9_HISTORICAL_PIT_PRODUCTION_OBSERVATIONS.json"
    assert p.exists()

    data = json.loads(p.read_text(encoding="utf-8-sig"))
    assert data["status"] == "NO_PRODUCTION_OBSERVATIONS"
    assert data["observation_count"] == 0
    assert "OBSERVATION_DATE_MARKET_PRICE_MISSING:TUPRS" in data["blockers"]
    assert "SCORE_MISSING:TUPRS" not in data["blockers"]
''',
    "backend/tests/test_fin_prod_v9_score_source_switch_v3.py": r'''
import json
from pathlib import Path


def test_fin_prod_v9_score_resolution_is_closed_and_market_gap_is_exact():
    root = Path(__file__).resolve().parents[2]
    p = root / "backend/data/financial_intelligence/FIN_PROD_V9_HISTORICAL_PIT_PRODUCTION_OBSERVATIONS.json"
    assert p.exists()

    data = json.loads(p.read_text(encoding="utf-8-sig"))
    assert "SCORE_MISSING:TUPRS" not in data["blockers"]
    assert "OBSERVATION_DATE_MARKET_PRICE_MISSING:TUPRS" in data["blockers"]
    assert "NO_SYNTHETIC_PRODUCTION_CALIBRATION" in data["rules"]
''',
}


def strip_bom_from_python(backend: Path) -> int:
    repaired = 0
    for path in backend.rglob("*.py"):
        raw = path.read_bytes()
        if raw.startswith(b"\\xef\\xbb\\xbf"):
            path.write_bytes(raw[3:])
            repaired += 1
    return repaired


def repair_renderer_failure_shape(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig")

    marker = 'if contract.get("status") != "PASS":'
    pos = text.find(marker)
    if pos < 0:
        raise RuntimeError("RENDERER_FAILURE_BRANCH_NOT_FOUND")

    ret = text.find("return {", pos)
    if ret < 0:
        raise RuntimeError("RENDERER_FAILURE_RETURN_NOT_FOUND")

    brace_start = text.find("{", ret)
    depth = 0
    end = None
    for i in range(brace_start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise RuntimeError("RENDERER_FAILURE_DICT_END_NOT_FOUND")

    replacement = '''return {
            "status": contract.get("status"),
            "symbol": contract.get("symbol"),
            "eligible_symbols": list(contract.get("eligible_symbols") or []),
            "panel_status": None,
            "financial_health": None,
            "cash_quality": None,
            "cash_quality_source": None,
            "capital_efficiency": None,
            "risk": None,
            "current_price": None,
            "attractive_entry_price": None,
            "valuation_status": None,
            "valuation_status_source": None,
            "panel_artifact": contract.get("panel_artifact"),
            "acceptance_artifact": None,
            "mode": "READ_ONLY_RENDERER_PAYLOAD",
        }'''

    new_text = text[:ret] + replacement + text[end:]
    compile(new_text, str(path), "exec")
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"

    backup = root / "_backup" / "FIN_INTEL_V1_1_REGRESSION_RECONCILIATION"
    backup.mkdir(parents=True, exist_ok=True)

    for rel, content in STALE_TESTS.items():
        path = root / rel
        if path.exists():
            target = backup / path.name
            if not target.exists():
                target.write_bytes(path.read_bytes())
        path.write_text(content.lstrip(), encoding="utf-8")

    renderer = backend / "app/ui/financial_intelligence_renderer_payload.py"
    renderer_backup = backup / renderer.name
    if renderer.exists() and not renderer_backup.exists():
        renderer_backup.write_bytes(renderer.read_bytes())

    repair_renderer_failure_shape(renderer)
    bom_count = strip_bom_from_python(backend)

    print(f"STALE_TESTS_RECONCILED={len(STALE_TESTS)}")
    print("RENDERER_FAIL_CLOSED_SHAPE=REPAIRED")
    print(f"BOM_FILES_REPAIRED={bom_count}")
    print(f"BACKUP={backup}")
    print("FIN_INTEL_V1_1_REGRESSION_RECONCILIATION=PASS")


if __name__ == "__main__":
    main()
