from __future__ import annotations

import ast
import re
import shutil
from datetime import datetime
from pathlib import Path


LABEL = "Finansal Zekâ Paneli"


def public_renderer_function(renderer_path: Path) -> str:
    text = renderer_path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)

    funcs = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            funcs.append(node.name)

    preferred = [
        name for name in funcs
        if "financial" in name.lower()
        and any(term in name.lower() for term in ("render", "dashboard", "panel"))
    ]
    if len(preferred) == 1:
        return preferred[0]

    renderish = [
        name for name in funcs
        if any(term in name.lower() for term in ("render", "dashboard", "panel"))
    ]
    if len(renderish) == 1:
        return renderish[0]

    raise RuntimeError(f"SAFE_RENDERER_FUNCTION_NOT_UNIQUE={funcs}")


def find_import_insertion(lines: list[str]) -> int:
    last_import = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import = i
    return last_import + 1


def insert_navigation_label(text: str) -> tuple[str, bool]:
    if LABEL in text:
        return text, False

    # Exact insertion beside existing "Temel Analiz" string item.
    patterns = [
        r'(?m)^(\s*)(["\'])Temel Analiz\2(\s*,?\s*)$',
        r'(?m)^(\s*)(["\'])Temel Analiz\2(\s*,)(\s*#.*)?$',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            indent = m.group(1)
            quote = m.group(2)
            line = m.group(0)
            comma = "," if "," in line else ""
            insertion = f"\n{indent}{quote}{LABEL}{quote}{comma}"
            return text[:m.end()] + insertion + text[m.end():], True

    # Inline list fallback: exact literal occurrence inside a bracket/list expression.
    for quote in ('"', "'"):
        token = f"{quote}Temel Analiz{quote}"
        idx = text.find(token)
        if idx != -1:
            # Require nearby list syntax.
            left = text[max(0, idx-300):idx]
            right = text[idx:idx+300]
            if "[" in left and "]" in right:
                end = idx + len(token)
                return text[:end] + f", {quote}{LABEL}{quote}" + text[end:], True

    raise RuntimeError("SAFE_NAVIGATION_INSERTION_POINT_NOT_FOUND")


def insert_route(text: str, renderer_func: str) -> tuple[str, bool]:
    if LABEL in text and re.search(
        rf'analiz_modu\s*==\s*["\']{re.escape(LABEL)}["\']',
        text
    ):
        return text, False

    # Exact existing route anchor.
    anchor = re.search(
        r'(?m)^(?P<indent>\s*)elif\s+analiz_modu\s*==\s*(?P<q>["\'])Temel Analiz(?P=q)\s*:\s*$',
        text
    )
    if not anchor:
        raise RuntimeError("SAFE_ROUTE_ANCHOR_NOT_FOUND=Temel Analiz")

    indent = anchor.group("indent")
    q = anchor.group("q")

    # Find end of Temel Analiz branch by next elif/else at same indentation.
    start = anchor.start()
    after = anchor.end()
    next_branch = re.search(
        rf'(?m)^{re.escape(indent)}(?:elif\b|else\s*:)',
        text[after:]
    )
    if next_branch:
        insert_at = after + next_branch.start()
    else:
        insert_at = len(text)

    route = (
        f'{indent}elif analiz_modu == {q}{LABEL}{q}:\n'
        f'{indent}    {renderer_func}()\n'
    )
    return text[:insert_at] + route + text[insert_at:], True


def ensure_import(text: str, renderer_func: str) -> tuple[str, bool]:
    target = f"from app.ui.financial_intelligence_dashboard import {renderer_func}"
    if target in text:
        return text, False

    lines = text.splitlines()
    idx = find_import_insertion(lines)
    lines.insert(idx, target)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), True


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    dashboard = backend / "dashboard.py"
    renderer = backend / "app/ui/financial_intelligence_dashboard.py"

    if not dashboard.exists():
        raise FileNotFoundError(dashboard)
    if not renderer.exists():
        raise FileNotFoundError(renderer)

    renderer_func = public_renderer_function(renderer)

    original = dashboard.read_text(encoding="utf-8-sig")
    updated = original

    updated, import_changed = ensure_import(updated, renderer_func)
    updated, nav_changed = insert_navigation_label(updated)
    updated, route_changed = insert_route(updated, renderer_func)

    if not (LABEL in updated and
            re.search(rf'analiz_modu\s*==\s*["\']{re.escape(LABEL)}["\']', updated) and
            f"{renderer_func}()" in updated):
        raise RuntimeError("POSTCHECK_FAILED_BEFORE_WRITE")

    backup_dir = root / "_backup" / f"FIN_INTEL_V1_LIVE_ROUTE_{datetime.now():%Y%m%d_%H%M%S}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / "dashboard.py"
    shutil.copy2(dashboard, backup)

    dashboard.write_text(updated, encoding="utf-8")

    # Compile postcheck.
    compile(updated, str(dashboard), "exec")

    print(f"STATUS=PASS")
    print(f"RENDERER_FUNCTION={renderer_func}")
    print(f"IMPORT_CHANGED={import_changed}")
    print(f"NAVIGATION_CHANGED={nav_changed}")
    print(f"ROUTE_CHANGED={route_changed}")
    print(f"BACKUP={backup}")
    print(f"TARGET={dashboard}")
    print("FINANCIAL_INTELLIGENCE_V1_LIVE_ROUTE_REPAIR=PASS")


if __name__ == "__main__":
    main()
