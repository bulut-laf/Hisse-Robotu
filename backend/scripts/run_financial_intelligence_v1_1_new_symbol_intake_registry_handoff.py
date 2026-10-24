from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REGISTRY_NAME = "FINANCIAL_INTELLIGENCE_V1_1_MULTI_SYMBOL_REGISTRY.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _find_latest_intake(fi_dir: Path) -> Path | None:
    candidates = sorted(
        fi_dir.glob("FINANCIAL_INTELLIGENCE_V1_1_NEW_SYMBOL_INTAKE*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _extract_symbol(node: Any) -> str | None:
    if isinstance(node, dict):
        for key in ("symbol", "SYMBOL"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().upper()
        for value in node.values():
            found = _extract_symbol(value)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _extract_symbol(item)
            if found:
                return found
    return None


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    fi = root / "backend" / "data" / "financial_intelligence"

    registry_path = fi / REGISTRY_NAME
    if not registry_path.exists():
        raise FileNotFoundError(registry_path)

    registry = _load(registry_path)
    intake_path = _find_latest_intake(fi)

    if intake_path is None:
        payload = {
            "schema_version": "financial-intelligence-v1-1-new-symbol-intake-registry-handoff-v1",
            "status": "PASS_NO_INTAKE_ARTIFACT",
            "symbol": None,
            "registry_updated": False,
            "blockers": ["NEW_SYMBOL_INTAKE_ARTIFACT_MISSING"],
            "registry_artifact": str(registry_path),
        }
    else:
        intake = _load(intake_path)
        symbol = _extract_symbol(intake)

        if not symbol:
            payload = {
                "schema_version": "financial-intelligence-v1-1-new-symbol-intake-registry-handoff-v1",
                "status": "BLOCKED",
                "symbol": None,
                "registry_updated": False,
                "blockers": ["INTAKE_SYMBOL_MISSING"],
                "intake_artifact": str(intake_path),
                "registry_artifact": str(registry_path),
            }
        else:
            panel_path = fi / f"{symbol}_financial_intelligence_panel.json"
            symbols = list(registry.get("symbols") or [])
            existing = [x for x in symbols if x.get("symbol") == symbol]

            if existing:
                payload = {
                    "schema_version": "financial-intelligence-v1-1-new-symbol-intake-registry-handoff-v1",
                    "status": "PASS_ALREADY_REGISTERED",
                    "symbol": symbol,
                    "registry_updated": False,
                    "blockers": [],
                    "intake_artifact": str(intake_path),
                    "panel_artifact": str(panel_path) if panel_path.exists() else None,
                    "registry_artifact": str(registry_path),
                }
            elif not panel_path.exists():
                payload = {
                    "schema_version": "financial-intelligence-v1-1-new-symbol-intake-registry-handoff-v1",
                    "status": "PASS_WAITING_FOR_CANONICAL_PANEL",
                    "symbol": symbol,
                    "registry_updated": False,
                    "blockers": ["CANONICAL_PANEL_NOT_READY"],
                    "intake_artifact": str(intake_path),
                    "panel_artifact": str(panel_path),
                    "registry_artifact": str(registry_path),
                }
            else:
                # Do not duplicate registry construction logic here.
                # Handoff signals that canonical registry refresh is now required.
                payload = {
                    "schema_version": "financial-intelligence-v1-1-new-symbol-intake-registry-handoff-v1",
                    "status": "PASS_READY_FOR_REGISTRY_REFRESH",
                    "symbol": symbol,
                    "registry_updated": False,
                    "blockers": [],
                    "intake_artifact": str(intake_path),
                    "panel_artifact": str(panel_path),
                    "registry_artifact": str(registry_path),
                    "next_action": "RUN_MULTI_SYMBOL_REGISTRY_REFRESH",
                }

    out = fi / "FINANCIAL_INTELLIGENCE_V1_1_NEW_SYMBOL_INTAKE_REGISTRY_HANDOFF.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS={payload['status']}")
    print(f"SYMBOL={payload.get('symbol')}")
    print(f"REGISTRY_UPDATED={payload.get('registry_updated')}")
    print(f"BLOCKERS={payload.get('blockers')}")
    if payload.get("next_action"):
        print(f"NEXT_ACTION={payload['next_action']}")
    print(f"RESULT={out}")
    print("FINANCIAL_INTELLIGENCE_V1_1_NEW_SYMBOL_INTAKE_REGISTRY_HANDOFF=PASS")


if __name__ == "__main__":
    main()
