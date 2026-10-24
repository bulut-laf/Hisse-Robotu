from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable
import json
import re

from .financial_intelligence_production_v2 import build_symbol_manifest


ACCEPTANCE_RE = re.compile(
    r"^financial_intelligence_acceptance_(?P<symbol>[A-Z0-9.-]+)_(?P<year>\d{4})_(?P<period>.+)\.json$",
    re.IGNORECASE,
)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def discover_symbols(repo: str | Path) -> tuple[str, ...]:
    """
    Discover production symbols from canonical financial acceptance files.
    No watchlist/ranking/scanner mutation and no symbol invention.
    """
    data = Path(repo) / "backend" / "data"
    symbols: set[str] = set()

    if not data.exists():
        return ()

    for p in data.glob("financial_intelligence_acceptance_*.json"):
        m = ACCEPTANCE_RE.match(p.name)
        if not m:
            continue
        symbol = m.group("symbol").upper().strip()
        if symbol:
            symbols.add(symbol)

    return tuple(sorted(symbols))


def load_sector_map(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    raw = _load_json(p)
    if not isinstance(raw, dict):
        return {}
    return {
        str(k).upper().strip(): str(v).upper().strip()
        for k, v in raw.items()
        if str(k).strip() and str(v).strip()
    }


def _artifact_health(manifest: dict[str, Any]) -> dict[str, int]:
    counts = {
        "present_or_pass": 0,
        "missing": 0,
        "invalid": 0,
        "other": 0,
    }
    for stage in manifest.get("stages") or ():
        status = str(stage.get("status") or "").upper()
        if status.startswith("PASS") or status in {"PRESENT", "OK"}:
            counts["present_or_pass"] += 1
        elif status == "MISSING":
            counts["missing"] += 1
        elif status == "INVALID_JSON":
            counts["invalid"] += 1
        else:
            counts["other"] += 1
    return counts


def build_live_batch(
    *,
    repo: str | Path,
    symbols: Iterable[str] | None = None,
    sector_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    sector_map = {
        str(k).upper().strip(): str(v).upper().strip()
        for k, v in (sector_map or {}).items()
    }

    requested = tuple(
        dict.fromkeys(
            str(s).upper().strip()
            for s in (symbols or ())
            if str(s).strip()
        )
    )
    selected = requested or discover_symbols(repo)

    manifests: list[dict[str, Any]] = []
    for symbol in selected:
        m = build_symbol_manifest(
            repo=repo,
            symbol=symbol,
            sector=sector_map.get(symbol),
        )
        d = asdict(m)
        d["artifact_health"] = _artifact_health(d)
        manifests.append(d)

    readiness: dict[str, int] = {}
    sector_counts: dict[str, int] = {}
    warning_counts: dict[str, int] = {}
    blocker_counts: dict[str, int] = {}

    for m in manifests:
        r = str(m["decision_support_status"])
        readiness[r] = readiness.get(r, 0) + 1

        sec = str(m["sector_profile"])
        sector_counts[sec] = sector_counts.get(sec, 0) + 1

        for w in m.get("warnings") or ():
            warning_counts[str(w)] = warning_counts.get(str(w), 0) + 1

        for b in m.get("blockers") or ():
            blocker_counts[str(b)] = blocker_counts.get(str(b), 0) + 1

    ready_symbols = [
        m["symbol"]
        for m in manifests
        if m["decision_support_status"] == "READY_FOR_DECISION_SUPPORT"
    ]
    blocked_symbols = [
        m["symbol"]
        for m in manifests
        if m["decision_support_status"] == "BLOCKED_SOURCE"
    ]

    return {
        "status": "PASS",
        "mode": "READ_ONLY_LIVE_MULTI_SYMBOL_PIPELINE_V3",
        "symbol_source": "EXPLICIT" if requested else "CANONICAL_FINANCIAL_ACCEPTANCE_DISCOVERY",
        "symbols": manifests,
        "summary": {
            "total_symbols": len(manifests),
            "ready_for_decision_support": len(ready_symbols),
            "blocked_source": len(blocked_symbols),
            "readiness": readiness,
            "sector_profiles": sector_counts,
            "warnings": warning_counts,
            "blockers": blocker_counts,
        },
        "ready_symbols": ready_symbols,
        "blocked_symbols": blocked_symbols,
        "production_rules": [
            "Canonical financial acceptance files are the only automatic symbol discovery source.",
            "Existing FIN-PROD-V2 manifests are reused through the V2 orchestrator API.",
            "No scanner/ranking/watchlist output is used to invent symbols.",
            "No missing artifact becomes zero.",
            "No AL/SAT, scanner, ranking or portfolio mutation.",
            "This pipeline reports production readiness; it does not generate trade recommendations.",
        ],
        "schema_version": "fin-prod-v3-live-batch-v1",
    }


def save_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
