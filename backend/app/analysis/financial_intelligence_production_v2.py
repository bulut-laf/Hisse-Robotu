from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
import glob
import json


SECTOR_PROFILES: dict[str, dict[str, Any]] = {
    "INDUSTRIAL": {
        "valuation_models": ("DCF_FCFF", "EV_SALES", "P_E", "P_B"),
        "required_focus": ("margins", "cash_conversion", "capital_efficiency", "cyclicality"),
        "cyclicality_default": "MEDIUM",
    },
    "BANK": {
        "valuation_models": ("P_B", "ROE", "RESIDUAL_INCOME"),
        "required_focus": ("capital_adequacy", "asset_quality", "net_interest_margin", "roe"),
        "cyclicality_default": "MEDIUM",
    },
    "INSURANCE": {
        "valuation_models": ("P_B", "ROE", "EMBEDDED_VALUE_WHERE_AVAILABLE"),
        "required_focus": ("combined_ratio", "reserve_quality", "investment_income", "solvency"),
        "cyclicality_default": "MEDIUM",
    },
    "REIT": {
        "valuation_models": ("NAV", "P_NAV", "FFO_AFFO"),
        "required_focus": ("nav", "occupancy", "lease_quality", "debt_maturity"),
        "cyclicality_default": "MEDIUM",
    },
    "HOLDING": {
        "valuation_models": ("SOTP", "NAV_DISCOUNT"),
        "required_focus": ("subsidiary_value", "holding_discount", "net_cash_debt", "governance"),
        "cyclicality_default": "MEDIUM",
    },
    "UTILITY_ENERGY": {
        "valuation_models": ("DCF_FCFF", "EV_EBITDA", "REGULATED_ASSET_BASE_WHERE_AVAILABLE"),
        "required_focus": ("regulated_returns", "capex", "debt", "cash_flow_visibility"),
        "cyclicality_default": "LOW",
    },
    "GENERIC": {
        "valuation_models": ("DCF_FCFF", "P_E", "P_B"),
        "required_focus": ("financial_health", "cash_quality", "risk", "valuation"),
        "cyclicality_default": "UNKNOWN",
    },
}


SECTOR_ALIASES = {
    "SANAYI": "INDUSTRIAL",
    "INDUSTRIAL": "INDUSTRIAL",
    "BANKA": "BANK",
    "BANK": "BANK",
    "BANKING": "BANK",
    "SIGORTA": "INSURANCE",
    "INSURANCE": "INSURANCE",
    "GYO": "REIT",
    "REIT": "REIT",
    "HOLDING": "HOLDING",
    "ENERJI": "UTILITY_ENERGY",
    "ENERGY": "UTILITY_ENERGY",
    "UTILITY": "UTILITY_ENERGY",
    "UTILITY_ENERGY": "UTILITY_ENERGY",
}


@dataclass(frozen=True)
class ArtifactStage:
    stage: str
    path: str | None
    status: str
    blocker: str | None = None


@dataclass(frozen=True)
class SymbolPipelineManifest:
    symbol: str
    sector_profile: str
    sector_routing: dict[str, Any]
    stages: tuple[ArtifactStage, ...]
    decision_support_status: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    read_only: bool = True
    schema_version: str = "fin-prod-v2-manifest-v1"


def _load(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def resolve_sector_profile(sector: str | None) -> tuple[str, dict[str, Any], tuple[str, ...]]:
    if not sector:
        return "GENERIC", SECTOR_PROFILES["GENERIC"], ("SECTOR_NOT_SUPPLIED_GENERIC_ROUTE",)
    key = SECTOR_ALIASES.get(str(sector).strip().upper(), "GENERIC")
    warnings = () if key != "GENERIC" else ("SECTOR_UNRECOGNIZED_GENERIC_ROUTE",)
    return key, SECTOR_PROFILES[key], warnings


def _latest(glob_pattern: str) -> Path | None:
    xs = [Path(p) for p in glob.glob(glob_pattern)]
    if not xs:
        return None
    return max(xs, key=lambda p: p.stat().st_mtime)


def discover_symbol_artifacts(repo: str | Path, symbol: str) -> dict[str, Path | None]:
    repo = Path(repo)
    symbol = symbol.upper().strip()
    fi = repo / "backend" / "data" / "financial_intelligence"
    data = repo / "backend" / "data"

    return {
        "financial_core": _latest(str(data / f"financial_intelligence_acceptance_{symbol}_*.json")),
        "market_ownership": fi / f"{symbol}_market_ownership_acceptance.json",
        "fair_value": fi / f"{symbol}_fair_value_acceptance.json",
        "investability": fi / f"{symbol}_investability_production_closure.json",
    }


def _stage_from_json(stage: str, path: Path | None, *, required: bool) -> ArtifactStage:
    if path is None or not path.exists():
        return ArtifactStage(
            stage=stage,
            path=str(path) if path else None,
            status="MISSING",
            blocker=f"{stage.upper()}_MISSING" if required else None,
        )

    payload = _load(path)
    if payload is None:
        return ArtifactStage(
            stage=stage,
            path=str(path),
            status="INVALID_JSON",
            blocker=f"{stage.upper()}_INVALID_JSON" if required else None,
        )

    raw_status = str(payload.get("status") or "PRESENT").upper()

    # Acceptance outputs may intentionally use PASS_CLOSED_WITH_EXPLICIT_BLOCKERS.
    if raw_status.startswith("PASS") or raw_status in {"PRESENT", "OK"}:
        return ArtifactStage(stage=stage, path=str(path), status=raw_status)

    return ArtifactStage(
        stage=stage,
        path=str(path),
        status=raw_status,
        blocker=f"{stage.upper()}_NOT_ACCEPTED" if required else None,
    )


def build_symbol_manifest(
    *,
    repo: str | Path,
    symbol: str,
    sector: str | None = None,
) -> SymbolPipelineManifest:
    symbol = symbol.upper().strip()
    sector_key, route, sector_warnings = resolve_sector_profile(sector)
    paths = discover_symbol_artifacts(repo, symbol)

    stages = (
        _stage_from_json("financial_core", paths["financial_core"], required=True),
        _stage_from_json("market_ownership", paths["market_ownership"], required=False),
        _stage_from_json("fair_value", paths["fair_value"], required=False),
        _stage_from_json("investability", paths["investability"], required=False),
    )

    blockers = [s.blocker for s in stages if s.blocker]

    inv_payload = _load(paths["investability"])
    warnings = list(sector_warnings)

    if inv_payload:
        for item in inv_payload.get("unresolved_blockers") or ():
            warnings.append(str(item))

    if blockers:
        status = "BLOCKED_SOURCE"
    elif paths["investability"] and paths["investability"].exists():
        status = "READY_FOR_DECISION_SUPPORT"
    elif paths["fair_value"] and paths["fair_value"].exists():
        status = "READY_PARTIAL_VALUATION"
    else:
        status = "READY_FINANCIAL_CORE_ONLY"

    return SymbolPipelineManifest(
        symbol=symbol,
        sector_profile=sector_key,
        sector_routing=route,
        stages=stages,
        decision_support_status=status,
        blockers=tuple(dict.fromkeys(blockers)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def build_batch_manifest(
    *,
    repo: str | Path,
    symbols: Iterable[str],
    sector_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    sector_map = {str(k).upper(): str(v) for k, v in (sector_map or {}).items()}
    manifests = [
        build_symbol_manifest(
            repo=repo,
            symbol=s,
            sector=sector_map.get(str(s).upper()),
        )
        for s in symbols
        if str(s).strip()
    ]

    counts: dict[str, int] = {}
    for m in manifests:
        counts[m.decision_support_status] = counts.get(m.decision_support_status, 0) + 1

    return {
        "status": "PASS",
        "mode": "READ_ONLY_PRODUCTION_EXPANSION_V2",
        "symbols": [asdict(m) for m in manifests],
        "summary": counts,
        "production_rules": [
            "Existing FIN-001..016 outputs are reused; no duplicate scoring engine.",
            "Sector routing is explicit and fail-safe; unknown sectors use GENERIC.",
            "Missing artifacts remain missing and do not become zero.",
            "AL/SAT, scanner, ranking and portfolio outputs are not mutated.",
            "This orchestrator is a manifest/orchestration layer, not a recommendation engine.",
        ],
        "schema_version": "fin-prod-v2-batch-v1",
    }


def save_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
