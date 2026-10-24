from __future__ import annotations

from pathlib import Path
from typing import Any

from app.analysis.financial_intelligence_selector_aware_panel import (
    build_selector_aware_financial_intelligence_panel,
)


def build_financial_intelligence_renderer_contract(
    project_root: str | Path,
    *,
    symbol: str | None = None,
) -> dict[str, Any]:
    data = build_selector_aware_financial_intelligence_panel(
        project_root,
        symbol=symbol,
        include_not_ready=False,
    )

    if data.get("status") != "PASS":
        return {
            "status": data.get("status"),
            "symbol": data.get("resolved_symbol"),
            "eligible_symbols": list(data.get("eligible_symbols") or []),
            "panel": None,
            "panel_artifact": data.get("panel_artifact"),
            "mode": "READ_ONLY_RENDERER_CONTRACT",
        }

    return {
        "status": "PASS",
        "symbol": data.get("resolved_symbol"),
        "eligible_symbols": list(data.get("eligible_symbols") or []),
        "panel": data.get("panel"),
        "panel_artifact": data.get("panel_artifact"),
        "mode": "READ_ONLY_RENDERER_CONTRACT",
    }


__all__ = ["build_financial_intelligence_renderer_contract"]
