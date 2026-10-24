from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(r"D:\Projects\Hisse-Robotu")
DASHBOARD = PROJECT_ROOT / "backend" / "dashboard.py"

IMPORT_LINE = (
    "from backend.app.ui.market_context_dashboard import "
    "render_market_context_dashboard\n"
)
MENU_LABEL = "Seans Öncesi Bağlam"


def insert_import(source: str) -> str:
    if "render_market_context_dashboard" in source:
        return source

    anchor = "import streamlit as st\n"
    if anchor not in source:
        raise RuntimeError("Streamlit import anchor bulunamadı.")

    return source.replace(anchor, anchor + "\n" + IMPORT_LINE, 1)


def insert_menu_item(source: str) -> str:
    if f'"{MENU_LABEL}"' in extract_analiz_modlari_block(source):
        return source

    match = re.search(
        r"ANALIZ_MODLARI\s*=\s*\(\n(?P<body>.*?\n)\)",
        source,
        flags=re.DOTALL,
    )
    if not match:
        raise RuntimeError("ANALIZ_MODLARI tuple bulunamadı.")

    body = match.group("body")
    items = re.findall(r'^\s*"([^"]+)",\s*$', body, flags=re.MULTILINE)
    if not items:
        raise RuntimeError("ANALIZ_MODLARI seçenekleri okunamadı.")

    items.append(MENU_LABEL)

    # Mevcut projede analiz menüsü alfabetik tutuluyor.
    items = sorted(set(items), key=lambda value: value.casefold())

    indent_match = re.search(r'^(\s*)"[^"]+",\s*$', body, flags=re.MULTILINE)
    indent = indent_match.group(1) if indent_match else "    "
    new_body = "".join(f'{indent}"{item}",\n' for item in items)

    return source[: match.start("body")] + new_body + source[match.end("body") :]


def extract_analiz_modlari_block(source: str) -> str:
    match = re.search(
        r"ANALIZ_MODLARI\s*=\s*\(\n(?P<body>.*?\n)\)",
        source,
        flags=re.DOTALL,
    )
    return match.group("body") if match else ""


def insert_route(source: str) -> str:
    route_line = (
        '    elif analiz_modu == "Seans Öncesi Bağlam":\n'
        '        render_market_context_dashboard(\n'
        '            st,\n'
        '            project_root=Path(__file__).resolve().parents[1],\n'
        '        )\n'
    )

    if 'analiz_modu == "Seans Öncesi Bağlam"' in source:
        return source

    # Path zaten dashboard.py içinde import edilmişse yeni import gerekmez.
    if not re.search(r"^from pathlib import Path\b|^import pathlib\b", source, re.MULTILINE):
        # En güvenli sabit import alanına ekle.
        streamlit_anchor = "import streamlit as st\n"
        if streamlit_anchor not in source:
            raise RuntimeError("Path importu için anchor bulunamadı.")
        source = source.replace(
            streamlit_anchor,
            "from pathlib import Path\n\n" + streamlit_anchor,
            1,
        )

    # Ana yönlendirme zincirindeki ilk if'i kullan.
    first_if = '    if analiz_modu == "Tek Hisse":\n'
    pos = source.find(first_if)
    if pos == -1:
        raise RuntimeError('Ana "Tek Hisse" yönlendirme anchoru bulunamadı.')

    # İlk branch'in sonunu, onu izleyen elif/else ile bul.
    search_start = pos + len(first_if)
    next_branch = re.search(
        r'^    (?:elif analiz_modu == |else:)',
        source[search_start:],
        flags=re.MULTILINE,
    )
    if not next_branch:
        raise RuntimeError("Ana analiz yönlendirme zincirinin devamı bulunamadı.")

    insertion_point = search_start + next_branch.start()
    return source[:insertion_point] + route_line + source[insertion_point:]


def validate(source: str) -> None:
    checks = {
        "UI import": "render_market_context_dashboard" in source,
        "menü seçeneği": f'"{MENU_LABEL}"' in extract_analiz_modlari_block(source),
        "route": 'analiz_modu == "Seans Öncesi Bağlam"' in source,
        "Path": "Path(__file__).resolve().parents[1]" in source,
    }

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise RuntimeError("Patch doğrulaması başarısız: " + ", ".join(failed))


def main() -> None:
    if not DASHBOARD.exists():
        raise FileNotFoundError(DASHBOARD)

    original = DASHBOARD.read_text(encoding="utf-8")
    updated = insert_import(original)
    updated = insert_menu_item(updated)
    updated = insert_route(updated)
    validate(updated)

    if updated == original:
        print("Sprint-137E2 dashboard bağlantısı zaten mevcut.")
        return

    backup = DASHBOARD.with_name(
        "dashboard.py.sprint137e2."
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".bak"
    )
    shutil.copy2(DASHBOARD, backup)

    DASHBOARD.write_text(updated, encoding="utf-8")

    print(f"Dashboard güncellendi: {DASHBOARD}")
    print(f"Yedek: {backup}")


if __name__ == "__main__":
    main()
