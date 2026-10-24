from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend" / "dashboard.py"
MARKET_SCANNER = ROOT / "backend" / "app" / "analysis" / "market_scanner.py"


def _unparse(node: ast.AST) -> str:
    return ast.unparse(node).replace(" ", "")


def test_ranking_memory_capture_uses_full_filtered_research_not_display_slice():
    source = DASHBOARD.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assignments = []
    observation_calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name)
                and target.id == "_three_all_rows"
                for target in node.targets
            ):
                assignments.append(node.value)

        if isinstance(node, ast.Call):
            fn = node.func
            name = (
                fn.id
                if isinstance(fn, ast.Name)
                else fn.attr
                if isinstance(fn, ast.Attribute)
                else ""
            )
            if name == "observations_from_research_rows":
                observation_calls.append(node)

    assert len(assignments) == 1
    expression = _unparse(assignments[0])

    assert "sonuc.filtrelenmis.adaylar" in expression
    assert "aday_tablosu_kayitlari(sonuc)" not in expression
    assert "sonuc.adaylar" not in expression

    assert any(
        any(
            keyword.arg == "rows"
            and isinstance(keyword.value, ast.Name)
            and keyword.value.id == "_three_all_rows"
            for keyword in call.keywords
        )
        for call in observation_calls
    )


def test_display_helper_remains_display_only_and_is_not_repurposed():
    source = MARKET_SCANNER.read_text(encoding="utf-8")

    assert "filtrelenmis.adaylar[: istek.maksimum_aday]" in source

    tree = ast.parse(source)
    helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "aday_tablosu_kayitlari"
    )

    helper_source = ast.unparse(helper).replace(" ", "")
    assert "enumerate(sonuc.adaylar,start=1)" in helper_source


def test_contract_keeps_capture_observation_only():
    source = DASHBOARD.read_text(encoding="utf-8")

    assert "RANKING_JUMP_V1_BLOCK1" in source
    assert "observations_from_research_rows" in source
    assert "RankObservationJsonlStore().append_snapshot" in source