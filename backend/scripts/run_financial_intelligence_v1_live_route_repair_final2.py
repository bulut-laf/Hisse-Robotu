from __future__ import annotations

import ast
import re
import shutil
from datetime import datetime
from pathlib import Path

LABEL = "Finansal Zekâ Paneli"
ANCHOR = "Temel Analiz"
MODULE_ALIAS = "_fin_intel_ui"


def choose_zero_arg_renderer(renderer: Path) -> str:
    text = renderer.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)

    candidates = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue

        args = node.args
        positional = list(args.posonlyargs) + list(args.args)
        required_pos = len(positional) - len(args.defaults)
        required_kwonly = sum(1 for d in args.kw_defaults if d is None)

        if required_pos == 0 and required_kwonly == 0:
            score = 0
            lname = node.name.lower()
            if "financial" in lname:
                score += 4
            if "intelligence" in lname:
                score += 4
            if "panel" in lname:
                score += 3
            if "dashboard" in lname:
                score += 3
            if "render" in lname:
                score += 2
            candidates.append((score, node.lineno, node.name))

    if not candidates:
        raise RuntimeError("NO_ZERO_ARG_PUBLIC_RENDERER")

    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    best = candidates[0]

    # Fail closed only if top semantic score is tied among different funcs.
    same = [c for c in candidates if c[0] == best[0]]
    if best[0] == 0 and len(same) > 1:
        raise RuntimeError(f"AMBIGUOUS_ZERO_ARG_RENDERERS={[c[2] for c in same]}")

    return best[2]


def ensure_module_import(lines: list[str]) -> tuple[list[str], bool]:
    stmt = f"from app.ui import financial_intelligence_dashboard as {MODULE_ALIAS}"
    if any(line.strip() == stmt for line in lines):
        return lines, False

    insert_at = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            insert_at = i + 1

    lines.insert(insert_at, stmt)
    return lines, True


def clone_navigation(lines: list[str]) -> tuple[list[str], bool]:
    if any(LABEL in line and "analiz_modu" not in line for line in lines):
        return lines, False

    candidates = []
    for i, line in enumerate(lines):
        if ANCHOR not in line or "analiz_modu" in line:
            continue
        if f'"{ANCHOR}"' not in line and f"'{ANCHOR}'" not in line:
            continue
        if line.lstrip().startswith("#"):
            continue
        candidates.append((i, line))

    if not candidates:
        raise RuntimeError("NAVIGATION_ANCHOR_LINE_NOT_FOUND")

    # Prefer navigation config context.
    chosen = candidates[0]
    for i, line in candidates:
        window = "\n".join(lines[max(0, i-50):i+10])
        if "AKIS_MODULLERI" in window or "KULLANIM_AKISI" in window:
            chosen = (i, line)
            break

    i, line = chosen
    cloned = line.replace(f'"{ANCHOR}"', f'"{LABEL}"').replace(f"'{ANCHOR}'", f"'{LABEL}'")
    if cloned == line:
        raise RuntimeError("NAVIGATION_CLONE_FAILED")
    lines.insert(i + 1, cloned)
    return lines, True


def ensure_route(lines: list[str], func: str) -> tuple[list[str], bool]:
    route_pattern = re.compile(r'analiz_modu\s*==\s*(["\'])Finansal Zekâ Paneli\1')
    if any(route_pattern.search(line) for line in lines):
        # If route exists, ensure call exists nearby.
        return lines, False

    temel_re = re.compile(r'^(\s*)elif\s+analiz_modu\s*==\s*(["\'])Temel Analiz\2\s*:\s*$')
    for i, line in enumerate(lines):
        m = temel_re.match(line)
        if not m:
            continue
        indent, quote = m.group(1), m.group(2)
        lines[i:i] = [
            f"{indent}elif analiz_modu == {quote}{LABEL}{quote}:",
            f"{indent}    {MODULE_ALIAS}.{func}()",
        ]
        return lines, True

    raise RuntimeError("TEMEL_ANALIZ_ROUTE_ANCHOR_NOT_FOUND")


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    dashboard = backend / "dashboard.py"
    renderer = backend / "app/ui/financial_intelligence_dashboard.py"

    if not dashboard.exists():
        raise FileNotFoundError(dashboard)
    if not renderer.exists():
        raise FileNotFoundError(renderer)

    func = choose_zero_arg_renderer(renderer)

    original = dashboard.read_text(encoding="utf-8-sig")
    newline = "\r\n" if "\r\n" in original else "\n"
    lines = original.splitlines()

    lines, import_changed = ensure_module_import(lines)
    lines, nav_changed = clone_navigation(lines)
    lines, route_changed = ensure_route(lines, func)

    updated = newline.join(lines) + (newline if original.endswith(("\n", "\r\n")) else "")

    expected_import = f"from app.ui import financial_intelligence_dashboard as {MODULE_ALIAS}"
    expected_call = f"{MODULE_ALIAS}.{func}()"

    checks = {
        "label": LABEL in updated,
        "route": bool(re.search(r'analiz_modu\s*==\s*(["\'])Finansal Zekâ Paneli\1', updated)),
        "import": expected_import in updated,
        "call": expected_call in updated,
        "temel_preserved": ANCHOR in updated,
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        raise RuntimeError(f"IN_MEMORY_POSTCHECK_FAILED={failed};FUNC={func};EXPECTED_CALL={expected_call}")

    compile(updated, str(dashboard), "exec")

    backup_dir = root / "_backup" / f"FIN_INTEL_V1_LIVE_ROUTE_FINAL2_{datetime.now():%Y%m%d_%H%M%S}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "dashboard.py"
    shutil.copy2(dashboard, backup)

    dashboard.write_text(updated, encoding="utf-8")

    disk = dashboard.read_text(encoding="utf-8")
    compile(disk, str(dashboard), "exec")
    if expected_import not in disk or expected_call not in disk or LABEL not in disk:
        raise RuntimeError("DISK_POSTCHECK_FAILED")

    print("STATUS=PASS")
    print(f"RENDERER_FUNCTION={func}")
    print(f"RENDERER_CALL={expected_call}")
    print(f"IMPORT_CHANGED={import_changed}")
    print(f"NAVIGATION_CHANGED={nav_changed}")
    print(f"ROUTE_CHANGED={route_changed}")
    print(f"BACKUP={backup}")
    print(f"TARGET={dashboard}")
    print("FINANCIAL_INTELLIGENCE_V1_LIVE_ROUTE_REPAIR_FINAL2=PASS")


if __name__ == "__main__":
    main()
