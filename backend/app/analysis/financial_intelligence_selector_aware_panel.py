from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.analysis.financial_intelligence_symbol_selector import (
    build_financial_intelligence_symbol_selector,
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_selector_aware_financial_intelligence_panel(
    project_root: str | Path,
    *,
    symbol: str | None = None,
    include_not_ready: bool = False,
) -> dict[str, Any]:
    root = Path(project_root)

    selector = build_financial_intelligence_symbol_selector(
        root,
        include_not_ready=include_not_ready,
    )

    eligible = list(selector.get("symbols") or [])

    requested = symbol.strip().upper() if isinstance(symbol, str) and symbol.strip() else None
    resolved = requested or selector.get("default_symbol")

    if selector.get("status") != "PASS":
        return {
            "status": "SELECTOR_NOT_READY",
            "requested_symbol": requested,
            "resolved_symbol": None,
            "eligible_symbols": eligible,
            "panel": None,
            "selector": selector,
            "mode": "READ_ONLY_PANEL_ADAPTER",
        }

    if resolved not in eligible:
        return {
            "status": "SYMBOL_NOT_ELIGIBLE",
            "requested_symbol": requested,
            "resolved_symbol": resolved,
            "eligible_symbols": eligible,
            "panel": None,
            "selector": selector,
            "mode": "READ_ONLY_PANEL_ADAPTER",
        }

    panel_path = (
        root
        / "backend"
        / "data"
        / "financial_intelligence"
        / f"{resolved}_financial_intelligence_panel.json"
    )

    if not panel_path.exists():
        return {
            "status": "PANEL_ARTIFACT_MISSING",
            "requested_symbol": requested,
            "resolved_symbol": resolved,
            "eligible_symbols": eligible,
            "panel": None,
            "panel_artifact": str(panel_path),
            "selector": selector,
            "mode": "READ_ONLY_PANEL_ADAPTER",
        }

    panel = _load_json(panel_path)

    return {
        "status": "PASS",
        "requested_symbol": requested,
        "resolved_symbol": resolved,
        "eligible_symbols": eligible,
        "panel": panel,
        "panel_artifact": str(panel_path),
        "selector": selector,
        "mode": "READ_ONLY_PANEL_ADAPTER",
    }


__all__ = ["build_selector_aware_financial_intelligence_panel"]
