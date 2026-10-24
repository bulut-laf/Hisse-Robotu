from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REGISTRY_FILE = "FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_REGISTRY.json"


def _load_registry(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_financial_intelligence_symbol_selector(
    project_root: str | Path,
    *,
    include_not_ready: bool = False,
) -> dict[str, Any]:
    root = Path(project_root)
    registry_path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / REGISTRY_FILE
    )

    if not registry_path.exists():
        return {
            "status": "REGISTRY_MISSING",
            "symbols": [],
            "default_symbol": None,
            "registry_artifact": str(registry_path),
        }

    registry = _load_registry(registry_path)
    rows = list(registry.get("symbols") or [])

    if not include_not_ready:
        rows = [row for row in rows if row.get("release_ready") is True]

    symbols = sorted({
        str(row.get("symbol")).strip().upper()
        for row in rows
        if row.get("symbol")
    })

    default_symbol = "TUPRS" if "TUPRS" in symbols else (symbols[0] if symbols else None)

    return {
        "status": "PASS" if symbols else "NO_ELIGIBLE_SYMBOLS",
        "symbols": symbols,
        "default_symbol": default_symbol,
        "symbol_count": len(symbols),
        "include_not_ready": include_not_ready,
        "registry_artifact": str(registry_path),
        "mode": "READ_ONLY_SELECTOR",
    }


__all__ = ["build_financial_intelligence_symbol_selector"]
