from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest


def _load_patcher():
    path = Path("tools/patch_sprint182_pdf_fallback.py")
    spec = importlib.util.spec_from_file_location("sprint182_patcher", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_s182_wrapper_layers_fallback_before_stable_s157_dashboard():
    source = Path("backend/app/ui/market_context_dashboard_s182.py").read_text(encoding="utf-8")
    assert "market_context_dashboard_s157" in source
    assert "RESET_AFTER_SAVE_KEY" in source
    assert "render_scanned_pdf_fallback(st)" in source
    assert "_render_market_context_dashboard_s157(st, project_root=project_root)" in source
    assert source.index("render_scanned_pdf_fallback(st)") < source.index(
        "_render_market_context_dashboard_s157(st, project_root=project_root)"
    )


def _rev3_runtime_text() -> str:
    return (
        "from backend.app.ui.market_context_dashboard import render_market_context_dashboard\n"
        "from backend.app.ui.market_context_dashboard_s182 import render_market_context_dashboard as _sprint182_render_market_context_dashboard\n"
        "\n"
        "render_market_context_dashboard = _sprint182_render_market_context_dashboard\n"
        "from backend.app.ui.market_context_dashboard_s157 import render_market_context_dashboard as render_market_context_dashboard_s157\n"
        "render_market_context_dashboard = render_market_context_dashboard_s157\n"
        "\n"
        "def run(analiz_modu, st, project_root):\n"
        "    if analiz_modu == 'x':\n"
        "        return None\n"
        "    elif analiz_modu == \"Seans Öncesi Bağlam\":\n"
        "        return render_market_context_dashboard(st, project_root=project_root)\n"
    )


def _last_target_assignment_value(source: str) -> str | None:
    tree = ast.parse(source)
    values: list[str | None] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == "render_market_context_dashboard":
            values.append(node.value.id if isinstance(node.value, ast.Name) else None)
    return values[-1] if values else None


def test_patcher_preserves_legacy_contracts_and_makes_s182_the_final_runtime_binding(tmp_path: Path):
    patcher = _load_patcher()
    dashboard = tmp_path / "dashboard.py"
    dashboard.write_text(_rev3_runtime_text(), encoding="utf-8")

    assert patcher.patch_dashboard(dashboard) == "patched"
    updated = dashboard.read_text(encoding="utf-8")

    assert patcher.LEGACY_IMPORT in updated
    assert patcher.S157_IMPORT in updated
    assert patcher.S157_REBIND_LINE in updated
    assert patcher.WRAPPER_IMPORT in updated
    assert updated.count(patcher.REBIND_LINE) == 1
    assert _last_target_assignment_value(updated) == patcher.WRAPPER_ALIAS
    assert "render_market_context_dashboard(" in updated


def test_patcher_is_idempotent_after_final_runtime_binding(tmp_path: Path):
    patcher = _load_patcher()
    dashboard = tmp_path / "dashboard.py"
    dashboard.write_text(_rev3_runtime_text(), encoding="utf-8")

    assert patcher.patch_dashboard(dashboard) == "patched"
    first = dashboard.read_text(encoding="utf-8")
    assert patcher.patch_dashboard(dashboard) == "already"
    second = dashboard.read_text(encoding="utf-8")

    assert second == first
    assert second.count(patcher.LEGACY_IMPORT) == 1
    assert second.count(patcher.S157_IMPORT) == 1
    assert second.count(patcher.WRAPPER_IMPORT) == 1
    assert second.count(patcher.REBIND_LINE) == 1


def test_patcher_rejects_missing_s157_legacy_rebind(tmp_path: Path):
    patcher = _load_patcher()
    dashboard = tmp_path / "dashboard.py"
    source = _rev3_runtime_text().replace(
        "render_market_context_dashboard = render_market_context_dashboard_s157\n",
        "",
    )
    dashboard.write_text(source, encoding="utf-8")
    with pytest.raises(RuntimeError, match="Sprint-157 legacy runtime rebind"):
        patcher.inspect_dashboard(dashboard)
