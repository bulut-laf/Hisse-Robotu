from __future__ import annotations

import ast
import re
import shutil
from datetime import datetime
from pathlib import Path

LABEL = "Finansal Zekâ Paneli"
ANCHOR = "Temel Analiz"


def choose_renderer(renderer: Path) -> str:
    text = renderer.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    funcs = [
        n.name for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not n.name.startswith("_")
    ]
    ranked = [
        f for f in funcs
        if "financial" in f.lower()
        and any(k in f.lower() for k in ("render", "panel", "dashboard"))
    ]
    if ranked:
        return ranked[0]
    ranked = [f for f in funcs if any(k in f.lower() for k in ("render", "panel", "dashboard"))]
    if ranked:
        return ranked[0]
    if len(funcs) == 1:
        return funcs[0]
    raise RuntimeError(f"RENDERER_FUNCTION_NOT_RESOLVED={funcs}")


def add_import(lines: list[str], func: str) -> tuple[list[str], bool]:
    stmt = f"from app.ui.financial_intelligence_dashboard import {func}"
    if any(stmt == line.strip() for line in lines):
        return lines, False

    insert_at = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            insert_at = i + 1
    lines.insert(insert_at, stmt)
    return lines, True


def clone_navigation_line(lines: list[str]) -> tuple[list[str], bool]:
    if any(LABEL in line and "analiz_modu" not in line for line in lines):
        return lines, False

    candidates = []
    for i, line in enumerate(lines):
        if ANCHOR not in line:
            continue
        stripped = line.strip()
        if "analiz_modu" in line:
            continue
        if stripped.startswith("#"):
            continue
        if re.search(r"\b(if|elif|while|for)\b", stripped):
            continue
        # Must be a quoted literal occurrence in a data/config line.
        if f'"{ANCHOR}"' not in line and f"'{ANCHOR}'" not in line:
            continue
        candidates.append((i, line))

    if not candidates:
        raise RuntimeError("NAVIGATION_ANCHOR_LINE_NOT_FOUND")

    # Prefer lines inside the known navigation config neighborhood.
    chosen = None
    for i, line in candidates:
        window = "\n".join(lines[max(0, i-40):i+10])
        if "AKIS_MODULLERI" in window or "KULLANIM_AKISI" in window:
            chosen = (i, line)
            break
    if chosen is None:
        chosen = candidates[0]

    i, line = chosen
    cloned = line.replace(f'"{ANCHOR}"', f'"{LABEL}"').replace(f"'{ANCHOR}'", f"'{LABEL}'")
    if cloned == line:
        raise RuntimeError("NAVIGATION_CLONE_REPLACE_FAILED")

    lines.insert(i + 1, cloned)
    return lines, True


def add_route_before_temel(lines: list[str], func: str) -> tuple[list[str], bool]:
    if any(LABEL in line and "analiz_modu" in line for line in lines):
        return lines, False

    route_re = re.compile(r'^(\s*)elif\s+analiz_modu\s*==\s*(["\'])Temel Analiz\2\s*:\s*$')
    for i, line in enumerate(lines):
        m = route_re.match(line)
        if not m:
            continue
        indent = m.group(1)
        quote = m.group(2)
        block = [
            f"{indent}elif analiz_modu == {quote}{LABEL}{quote}:",
            f"{indent}    {func}()",
        ]
        lines[i:i] = block
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

    original = dashboard.read_text(encoding="utf-8-sig")
    newline = "\r\n" if "\r\n" in original else "\n"
    lines = original.splitlines()

    func = choose_renderer(renderer)
    lines, import_changed = add_import(lines, func)
    lines, nav_changed = clone_navigation_line(lines)
    lines, route_changed = add_route_before_temel(lines, func)

    updated = newline.join(lines) + (newline if original.endswith(("\n", "\r\n")) else "")

    # Strong in-memory postchecks before any write.
    if LABEL not in updated:
        raise RuntimeError("POSTCHECK_LABEL_MISSING")
    if not re.search(r'analiz_modu\s*==\s*["\']Finansal Zekâ Paneli["\']', updated):
        raise RuntimeError("POSTCHECK_ROUTE_MISSING")
    if f"{func}()" not in updated:
        raise RuntimeError("POSTCHECK_RENDERER_CALL_MISSING")
    if ANCHOR not in updated:
        raise RuntimeError("POSTCHECK_TEMEL_ANALIZ_NOT_PRESERVED")

    compile(updated, str(dashboard), "exec")

    backup_dir = root / "_backup" / f"FIN_INTEL_V1_LIVE_ROUTE_FINAL_{datetime.now():%Y%m%d_%H%M%S}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "dashboard.py"
    shutil.copy2(dashboard, backup)

    dashboard.write_text(updated, encoding="utf-8", newline="")

    # Disk postcheck.
    disk = dashboard.read_text(encoding="utf-8")
    compile(disk, str(dashboard), "exec")
    if LABEL not in disk or f"{func}()" not in disk:
        raise RuntimeError("DISK_POSTCHECK_FAILED")

    print("STATUS=PASS")
    print(f"RENDERER_FUNCTION={func}")
    print(f"IMPORT_CHANGED={import_changed}")
    print(f"NAVIGATION_CHANGED={nav_changed}")
    print(f"ROUTE_CHANGED={route_changed}")
    print(f"BACKUP={backup}")
    print(f"TARGET={dashboard}")
    print("FINANCIAL_INTELLIGENCE_V1_LIVE_ROUTE_REPAIR_FINAL=PASS")


if __name__ == "__main__":
    main()
