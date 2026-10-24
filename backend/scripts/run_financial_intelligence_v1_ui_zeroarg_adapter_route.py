from __future__ import annotations

import ast
import re
import shutil
from datetime import datetime
from pathlib import Path

LABEL = "Finansal Zekâ Paneli"
ANCHOR = "Temel Analiz"
ADAPTER_NAME = "render_financial_intelligence_panel_entry"

KNOWN_PARAM_SOURCES = {
    "symbol": "'TUPRS'",
    "ticker": "'TUPRS'",
    "panel": "_panel",
    "panel_data": "_panel",
    "data": "_panel",
    "payload": "_panel",
    "artifact": "_panel",
    "artifact_data": "_panel",
    "project_root": "str(_root)",
    "root": "str(_root)",
    "backend_root": "str(_backend)",
    "data_dir": "str(_fi_dir)",
    "artifact_path": "str(_artifact)",
    "panel_path": "str(_artifact)",
}


def find_renderer_function(renderer_text: str) -> tuple[str, list[str]]:
    tree = ast.parse(renderer_text)
    candidates = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name.startswith("_") or node.name == ADAPTER_NAME:
            continue
        args = list(node.args.posonlyargs) + list(node.args.args)
        required_count = len(args) - len(node.args.defaults)
        required = [a.arg for a in args[:required_count]]
        required += [a.arg for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults) if d is None]
        if not required:
            continue
        if all(name in KNOWN_PARAM_SOURCES for name in required):
            lname = node.name.lower()
            score = 0
            for term, pts in (("financial",5),("intelligence",5),("panel",4),("dashboard",3),("render",3)):
                if term in lname:
                    score += pts
            candidates.append((score, node.lineno, node.name, required))

    if not candidates:
        raise RuntimeError("NO_RESOLVABLE_RENDERER_SIGNATURE")

    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    best = candidates[0]
    return best[2], best[3]


def build_adapter(renderer_func: str, required: list[str]) -> str:
    kwargs = ",\n        ".join(f"{name}={KNOWN_PARAM_SOURCES[name]}" for name in required)
    template = """

def __ADAPTER_NAME__():
    \"\"\"Zero-argument live dashboard entry for Financial Intelligence V1.\"\"\"
    import json as _json
    from pathlib import Path as _Path

    _backend = _Path(__file__).resolve().parents[2]
    _root = _backend.parent
    _fi_dir = _backend / "data" / "financial_intelligence"
    _artifact = _fi_dir / "TUPRS_financial_intelligence_panel.json"

    if not _artifact.exists():
        raise FileNotFoundError(f"FINANCIAL_INTELLIGENCE_PANEL_ARTIFACT_MISSING={_artifact}")

    _panel = _json.loads(_artifact.read_text(encoding="utf-8-sig"))
    if not isinstance(_panel, dict):
        raise RuntimeError("FINANCIAL_INTELLIGENCE_PANEL_ARTIFACT_INVALID")

    return __RENDERER_FUNC__(
        __KWARGS__
    )
"""
    return (
        template
        .replace("__ADAPTER_NAME__", ADAPTER_NAME)
        .replace("__RENDERER_FUNC__", renderer_func)
        .replace("__KWARGS__", kwargs)
    )


def ensure_adapter(renderer_path: Path) -> tuple[str, list[str], bool]:
    text = renderer_path.read_text(encoding="utf-8-sig")
    if re.search(rf"(?m)^def\s+{ADAPTER_NAME}\s*\(", text):
        return ADAPTER_NAME, [], False

    func, required = find_renderer_function(text)
    updated = text.rstrip() + build_adapter(func, required) + "\n"
    compile(updated, str(renderer_path), "exec")
    renderer_path.write_text(updated, encoding="utf-8")
    return func, required, True


def ensure_import(lines: list[str]) -> tuple[list[str], bool]:
    stmt = f"from app.ui.financial_intelligence_dashboard import {ADAPTER_NAME}"
    if any(line.strip() == stmt for line in lines):
        return lines, False

    idx = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            idx = i + 1
    lines.insert(idx, stmt)
    return lines, True


def ensure_nav(lines: list[str]) -> tuple[list[str], bool]:
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
        raise RuntimeError("NAVIGATION_ANCHOR_NOT_FOUND")

    i, line = candidates[0]
    for ci, cline in candidates:
        window = "\n".join(lines[max(0, ci-50):ci+10])
        if "AKIS_MODULLERI" in window or "KULLANIM_AKISI" in window:
            i, line = ci, cline
            break

    cloned = line.replace(f'"{ANCHOR}"', f'"{LABEL}"').replace(f"'{ANCHOR}'", f"'{LABEL}'")
    if cloned == line:
        raise RuntimeError("NAVIGATION_CLONE_FAILED")
    lines.insert(i + 1, cloned)
    return lines, True


def ensure_route(lines: list[str]) -> tuple[list[str], bool]:
    route_re = re.compile(r'analiz_modu\s*==\s*(["\'])Finansal Zekâ Paneli\1')
    if any(route_re.search(line) for line in lines):
        return lines, False

    temel_re = re.compile(r'^(\s*)elif\s+analiz_modu\s*==\s*(["\'])Temel Analiz\2\s*:\s*$')
    for i, line in enumerate(lines):
        m = temel_re.match(line)
        if not m:
            continue
        indent, quote = m.group(1), m.group(2)
        lines[i:i] = [
            f"{indent}elif analiz_modu == {quote}{LABEL}{quote}:",
            f"{indent}    {ADAPTER_NAME}()",
        ]
        return lines, True
    raise RuntimeError("TEMEL_ANALIZ_ROUTE_ANCHOR_NOT_FOUND")


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    dashboard = backend / "dashboard.py"
    renderer = backend / "app" / "ui" / "financial_intelligence_dashboard.py"

    if not dashboard.exists():
        raise FileNotFoundError(dashboard)
    if not renderer.exists():
        raise FileNotFoundError(renderer)

    backup_dir = root / "_backup" / f"FIN_INTEL_V1_UI_ZEROARG_{datetime.now():%Y%m%d_%H%M%S}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dashboard, backup_dir / "dashboard.py")
    shutil.copy2(renderer, backup_dir / "financial_intelligence_dashboard.py")

    renderer_func, required, adapter_changed = ensure_adapter(renderer)

    original = dashboard.read_text(encoding="utf-8-sig")
    newline = "\r\n" if "\r\n" in original else "\n"
    lines = original.splitlines()

    lines, import_changed = ensure_import(lines)
    lines, nav_changed = ensure_nav(lines)
    lines, route_changed = ensure_route(lines)

    updated = newline.join(lines) + (newline if original.endswith(("\n", "\r\n")) else "")
    compile(updated, str(dashboard), "exec")

    if LABEL not in updated:
        raise RuntimeError("POSTCHECK_LABEL_MISSING")
    if f"{ADAPTER_NAME}()" not in updated:
        raise RuntimeError("POSTCHECK_ADAPTER_CALL_MISSING")
    if ANCHOR not in updated:
        raise RuntimeError("POSTCHECK_TEMEL_ANALIZ_NOT_PRESERVED")

    dashboard.write_text(updated, encoding="utf-8")

    print("STATUS=PASS")
    print(f"RENDERER_FUNCTION={renderer_func}")
    print(f"RENDERER_REQUIRED_ARGS={required}")
    print(f"ADAPTER_CHANGED={adapter_changed}")
    print(f"IMPORT_CHANGED={import_changed}")
    print(f"NAVIGATION_CHANGED={nav_changed}")
    print(f"ROUTE_CHANGED={route_changed}")
    print(f"BACKUP={backup_dir}")
    print(f"DASHBOARD={dashboard}")
    print(f"RENDERER={renderer}")
    print("FINANCIAL_INTELLIGENCE_V1_UI_ZEROARG_ADAPTER_ROUTE=PASS")


if __name__ == "__main__":
    main()
