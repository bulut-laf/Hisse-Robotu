from __future__ import annotations

import ast
import sys
from pathlib import Path

LEGACY_MODULE = "backend.app.ui.market_context_dashboard"
S157_MODULE = "backend.app.ui.market_context_dashboard_s157"
NEW_MODULE = "backend.app.ui.market_context_dashboard_s182"
TARGET_NAME = "render_market_context_dashboard"
S157_ALIAS = "render_market_context_dashboard_s157"
WRAPPER_ALIAS = "_sprint182_render_market_context_dashboard"
LEGACY_IMPORT = f"from {LEGACY_MODULE} import {TARGET_NAME}"
S157_IMPORT = f"from {S157_MODULE} import {TARGET_NAME} as {S157_ALIAS}"
WRAPPER_IMPORT = f"from {NEW_MODULE} import {TARGET_NAME} as {WRAPPER_ALIAS}"
S157_REBIND_LINE = f"{TARGET_NAME} = {S157_ALIAS}"
REBIND_LINE = f"{TARGET_NAME} = {WRAPPER_ALIAS}"
ROUTE_ANCHOR = 'elif analiz_modu == "Seans Öncesi Bağlam":'


def _parse(text: str) -> ast.Module:
    try:
        return ast.parse(text)
    except SyntaxError as exc:
        raise RuntimeError(f"backend/dashboard.py Python sözdizimi geçersiz: {exc}") from exc


def _top_imports(tree: ast.Module, module: str, *, alias_name: str | None) -> list[ast.ImportFrom]:
    found: list[ast.ImportFrom] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.level != 0 or node.module != module:
            continue
        for alias in node.names:
            if alias.name != TARGET_NAME:
                continue
            effective = alias.asname or alias.name
            if effective == (alias_name or TARGET_NAME):
                found.append(node)
                break
    return found


def _target_assignments(tree: ast.Module) -> list[ast.Assign]:
    found: list[ast.Assign] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == TARGET_NAME:
            found.append(node)
    return found


def _assignment_value_name(node: ast.Assign) -> str | None:
    return node.value.id if isinstance(node.value, ast.Name) else None


def _validate_route_contract(text: str) -> None:
    if ROUTE_ANCHOR not in text:
        raise RuntimeError("Seans Öncesi Bağlam rotası bulunamadı.")
    if f"{TARGET_NAME}(" not in text:
        raise RuntimeError("Legacy Seans Öncesi Bağlam çağrı adı korunmuyor.")


def inspect_dashboard(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    tree = _parse(text)
    legacy = _top_imports(tree, LEGACY_MODULE, alias_name=None)
    wrapper = _top_imports(tree, NEW_MODULE, alias_name=WRAPPER_ALIAS)
    s157 = _top_imports(tree, S157_MODULE, alias_name=S157_ALIAS)
    assignments = _target_assignments(tree)

    if len(legacy) != 1:
        raise RuntimeError(
            "Sprint-182 Rev4 legacy import sözleşmesi güvenle belirlenemedi; "
            f"beklenen 1, bulunan {len(legacy)}."
        )
    if len(wrapper) != 1:
        raise RuntimeError(
            "Sprint-182 Rev4 wrapper alias importu güvenle belirlenemedi; "
            f"beklenen 1, bulunan {len(wrapper)}."
        )
    if len(s157) != 1:
        raise RuntimeError(
            "Sprint-182 Rev4 Sprint-157 alias importu güvenle belirlenemedi; "
            f"beklenen 1, bulunan {len(s157)}."
        )
    if not any(_assignment_value_name(node) == S157_ALIAS for node in assignments):
        raise RuntimeError("Sprint-157 legacy runtime rebind satırı bulunamadı.")

    _validate_route_contract(text)

    if not assignments:
        return "patchable"
    last_value = _assignment_value_name(assignments[-1])
    if last_value == WRAPPER_ALIAS:
        return "already"
    if last_value == S157_ALIAS:
        return "patchable"
    raise RuntimeError(
        "render_market_context_dashboard adı beklenmeyen bir ifadeye yeniden bağlanmış."
    )


def _remove_wrapper_rebinds(text: str) -> str:
    tree = _parse(text)
    wrapper_assignments = [
        node
        for node in _target_assignments(tree)
        if _assignment_value_name(node) == WRAPPER_ALIAS
    ]
    if not wrapper_assignments:
        return text

    lines = text.splitlines(keepends=True)
    remove_indexes: set[int] = set()
    for node in wrapper_assignments:
        start = node.lineno - 1
        end = (node.end_lineno or node.lineno) - 1
        remove_indexes.update(range(start, end + 1))
    return "".join(line for index, line in enumerate(lines) if index not in remove_indexes)


def patch_dashboard(path: Path) -> str:
    status = inspect_dashboard(path)
    if status == "already":
        return "already"

    text = path.read_text(encoding="utf-8")
    updated = _remove_wrapper_rebinds(text)
    tree = _parse(updated)

    related_nodes: list[ast.AST] = []
    related_nodes.extend(_top_imports(tree, LEGACY_MODULE, alias_name=None))
    related_nodes.extend(_top_imports(tree, NEW_MODULE, alias_name=WRAPPER_ALIAS))
    related_nodes.extend(_top_imports(tree, S157_MODULE, alias_name=S157_ALIAS))
    related_nodes.extend(_target_assignments(tree))
    if not related_nodes:
        raise RuntimeError("Sprint-182 Rev4 runtime wiring ankrajları bulunamadı.")

    last_node = max(related_nodes, key=lambda node: node.end_lineno or node.lineno)
    lines = updated.splitlines(keepends=True)
    anchor_index = (last_node.end_lineno or last_node.lineno)
    anchor_line = lines[(last_node.end_lineno or last_node.lineno) - 1]
    newline = "\r\n" if anchor_line.endswith("\r\n") else "\n"
    lines[anchor_index:anchor_index] = [REBIND_LINE + newline]
    updated = "".join(lines)

    if LEGACY_IMPORT not in updated:
        raise RuntimeError("Legacy Sprint-137E2 import satırı patch sırasında kayboldu.")
    if S157_IMPORT not in updated:
        raise RuntimeError("Sprint-157 legacy alias importu patch sırasında kayboldu.")
    if S157_REBIND_LINE not in updated:
        raise RuntimeError("Sprint-157 legacy runtime rebind satırı patch sırasında kayboldu.")
    if f"{TARGET_NAME}(" not in updated:
        raise RuntimeError("Legacy route çağrı adı patch sırasında kayboldu.")

    tmp_path = path.with_suffix(path.suffix + ".s182rev4check")
    try:
        tmp_path.write_text(updated, encoding="utf-8", newline="")
        if inspect_dashboard(tmp_path) != "already":
            raise RuntimeError("Sprint-182 Rev4 final runtime yönlendirmesi doğrulanamadı.")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    path.write_text(updated, encoding="utf-8", newline="")
    return "patched"


def main() -> int:
    args = sys.argv[1:]
    check_only = False
    if args and args[0] == "--check":
        check_only = True
        args = args[1:]
    if len(args) != 1:
        print("Kullanım: patch_sprint182_pdf_fallback.py [--check] <backend/dashboard.py>")
        return 2
    path = Path(args[0])
    if not path.is_file():
        print(f"Dashboard bulunamadı: {path}")
        return 2
    try:
        if check_only:
            status = inspect_dashboard(path)
            print(f"[OK] Sprint-182 Rev4 dashboard önkontrolü: {status}")
        else:
            status = patch_dashboard(path)
            print(f"[OK] Sprint-182 Rev4 final runtime yönlendirmesi: {status}")
    except Exception as exc:
        print(f"[HATA] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
