from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend" / "dashboard.py"
MARKET_SCANNER = ROOT / "backend" / "app" / "analysis" / "market_scanner.py"


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _dotted(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""


def test_ranking_memory_uses_dedicated_full_filtered_rows():
    source = DASHBOARD.read_text(encoding="utf-8")
    tree = ast.parse(source)

    dedicated = []
    observation_rows = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name)
                and target.id == "_ranking_memory_rows"
                for target in node.targets
            ):
                dedicated.append(node.value)

        if isinstance(node, ast.Call) and _dotted(node.func).endswith(
            "observations_from_research_rows"
        ):
            kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
            if "rows" in kwargs:
                observation_rows.append(kwargs["rows"])

    assert len(dedicated) == 1
    expr = ast.unparse(dedicated[0]).replace(" ", "")
    assert "sonuc.filtrelenmis.adaylar" in expr
    assert "sonuc.adaylar" not in expr
    assert "aday_tablosu_kayitlari(sonuc)" not in expr

    assert any(
        isinstance(rows, ast.Name)
        and rows.id == "_ranking_memory_rows"
        for rows in observation_rows
    )


def test_display_candidate_limit_contract_remains_unchanged():
    source = MARKET_SCANNER.read_text(encoding="utf-8")
    compact = source.replace(" ", "").replace("\n", "")

    assert "filtrelenmis.adaylar[:istek.maksimum_aday]" in compact


def test_patch_does_not_repurpose_existing_shared_rows():
    source = DASHBOARD.read_text(encoding="utf-8")

    # Existing display / three-system rows may continue to exist.
    # Ranking Memory must use its own dedicated row source.
    assert "_ranking_memory_rows" in source
    assert "rows=_ranking_memory_rows" in source.replace(" ", "")