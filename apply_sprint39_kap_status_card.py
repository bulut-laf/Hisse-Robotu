from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "backend" / "dashboard.py"
BACKUP = TARGET.with_suffix(".py.sprint39-kap-status-card.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def ensure_os_import(source: str) -> str:
    if "\nimport os\n" in source or source.startswith("import os\n"):
        return source

    anchor = "from __future__ import annotations\n"
    if anchor in source:
        return source.replace(anchor, anchor + "\nimport os\n", 1)

    return "import os\n" + source


def add_status_function(source: str) -> str:
    if "def kap_vbts_durum_karti_goster()" in source:
        return source

    function_text = 