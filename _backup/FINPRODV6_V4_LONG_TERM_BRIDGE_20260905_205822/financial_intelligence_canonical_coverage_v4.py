from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

SHORT_TERM_BLOCKER = "SHORT_TERM_CANONICAL_TECHNICAL_MARKET_CONTEXT"
LONG_TERM_BLOCKER = "LONG_TERM_CANONICAL_COVERAGE"

SHORT_TERM_FILE = "{symbol}_short_term_canonical_context.json"
LONG_TERM_FILE = "{symbol}_long_term_canonical_coverage.json"

PASS_STATUSES = {"PASS", "PRESENT", "VALID", "READY", "OK"}


@dataclass(frozen=True)
class CoverageArtifact:
    kind: str
    path: str
    status: str
    as_of_date: str | None
    warnings: tuple[str, ...]
    missing_fields: tuple[str, ...]


@dataclass(frozen=True)
class SymbolCoverage:
    symbol: str
    short_term: CoverageArtifact
    long_term: CoverageArtifact
    unresolved_blockers: tuple[str, ...]
    coverage_status: str


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def _status_pass(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        value = value.get("status")
    return str(value or "").upper().strip() in PASS_STATUSES


def _symbol_ok(payload: dict[str, Any], symbol: str) -> bool:
    return str(payload.get("symbol") or "").upper().strip() == symbol


def _canonical_ok(payload: dict[str, Any]) -> bool:
    return payload.get("canonical") is True or str(payload.get("source_mode") or "").upper() == "CANONICAL"



def _v5_short_term_v7a_ok(payload: dict[str, Any], symbol: str) -> bool:
    if str(payload.get("schema_version") or "").strip() != "fin-prod-v5-short-term-canonical-context-v7a":
        return False
    if not _symbol_ok(payload, symbol):
        return False
    if not _status_pass(payload.get("status")):
        return False
    if not _status_pass(payload.get("data_quality")):
        return False

    as_of = str(payload.get("as_of_date") or "").strip()
    if not as_of:
        return False

    market = payload.get("market_context")
    if not isinstance(market, dict):
        return False
    for key in ("technical_trend", "relative_strength", "volume_liquidity"):
        if market.get(key) in (None, ""):
            return False

    evidence = payload.get("metric_evidence")
    if not isinstance(evidence, dict):
        return False
    for key in ("technical_trend", "relative_strength", "volume_liquidity"):
        item = evidence.get(key)
        if not isinstance(item, dict):
            return False
        if str(item.get("status") or "").strip() != "EXACT_MOMENTUM_CANDIDATE_FIELD":
            return False
        if not str(item.get("source") or "").strip():
            return False
        if not str(item.get("key") or "").strip():
            return False

    price = payload.get("price_reference")
    if not isinstance(price, dict):
        return False
    price_date = str(price.get("date") or "").strip()
    cutoff = str(price.get("point_in_time_cutoff") or "").strip()
    if not price_date or cutoff != as_of or price_date > as_of:
        return False

    blockers = payload.get("blockers")
    if blockers not in (None, [], ()):
        return False

    return True


def _validate_short_term(path: Path, symbol: str) -> CoverageArtifact:
    if not path.exists():
        return CoverageArtifact(
            kind="SHORT_TERM",
            path=str(path),
            status="MISSING",
            as_of_date=None,
            warnings=(),
            missing_fields=("artifact",),
        )
    payload = _load_json(path)
    if payload is None:
        return CoverageArtifact(
            kind="SHORT_TERM",
            path=str(path),
            status="INVALID_JSON",
            as_of_date=None,
            warnings=("INVALID_JSON",),
            missing_fields=(),
        )

    missing: list[str] = []

    if _v5_short_term_v7a_ok(payload, symbol):
        pass
    else:
        if not _symbol_ok(payload, symbol):
            missing.append("symbol")
        if not _canonical_ok(payload):
            missing.append("canonical")
        if not str(payload.get("as_of_date") or "").strip():
            missing.append("as_of_date")
        if not _status_pass(payload.get("technical_context")):
            missing.append("technical_context")
        if not _status_pass(payload.get("market_context")):
            missing.append("market_context")
        if not _status_pass(payload.get("data_quality")):
            missing.append("data_quality")

    return CoverageArtifact(
        kind="SHORT_TERM",
        path=str(path),
        status="PASS" if not missing else "BLOCKED",
        as_of_date=str(payload.get("as_of_date") or "") or None,
        warnings=tuple(str(x) for x in payload.get("warnings") or ()),
        missing_fields=tuple(missing),
    )


def _validate_long_term(path: Path, symbol: str) -> CoverageArtifact:
    if not path.exists():
        return CoverageArtifact(
            kind="LONG_TERM",
            path=str(path),
            status="MISSING",
            as_of_date=None,
            warnings=(),
            missing_fields=("artifact",),
        )
    payload = _load_json(path)
    if payload is None:
        return CoverageArtifact(
            kind="LONG_TERM",
            path=str(path),
            status="INVALID_JSON",
            as_of_date=None,
            warnings=("INVALID_JSON",),
            missing_fields=(),
        )

    missing: list[str] = []
    if not _symbol_ok(payload, symbol):
        missing.append("symbol")
    if not _canonical_ok(payload):
        missing.append("canonical")
    if not str(payload.get("as_of_date") or "").strip():
        missing.append("as_of_date")
    if not _status_pass(payload.get("business_quality")):
        missing.append("business_quality")
    if not _status_pass(payload.get("governance")):
        missing.append("governance")
    if not _status_pass(payload.get("growth_context")):
        missing.append("growth_context")
    if not _status_pass(payload.get("data_quality")):
        missing.append("data_quality")

    return CoverageArtifact(
        kind="LONG_TERM",
        path=str(path),
        status="PASS" if not missing else "BLOCKED",
        as_of_date=str(payload.get("as_of_date") or "") or None,
        warnings=tuple(str(x) for x in payload.get("warnings") or ()),
        missing_fields=tuple(missing),
    )


def inspect_symbol_coverage(*, repo: str | Path, symbol: str) -> SymbolCoverage:
    symbol = str(symbol).upper().strip()
    root = Path(repo) / "backend" / "data" / "financial_intelligence"
    short_term = _validate_short_term(root / SHORT_TERM_FILE.format(symbol=symbol), symbol)
    long_term = _validate_long_term(root / LONG_TERM_FILE.format(symbol=symbol), symbol)

    blockers: list[str] = []
    if short_term.status != "PASS":
        blockers.append(SHORT_TERM_BLOCKER)
    if long_term.status != "PASS":
        blockers.append(LONG_TERM_BLOCKER)

    status = "READY_FULL_CANONICAL_COVERAGE" if not blockers else "BLOCKED_CANONICAL_COVERAGE"
    return SymbolCoverage(
        symbol=symbol,
        short_term=short_term,
        long_term=long_term,
        unresolved_blockers=tuple(blockers),
        coverage_status=status,
    )


def enrich_v3_batch(*, repo: str | Path, v3_batch: dict[str, Any]) -> dict[str, Any]:
    symbols_out: list[dict[str, Any]] = []
    fully_ready: list[str] = []
    coverage_blocked: list[str] = []

    for raw in v3_batch.get("symbols") or ():
        if not isinstance(raw, dict):
            continue
        symbol = str(raw.get("symbol") or "").upper().strip()
        if not symbol:
            continue

        cov = inspect_symbol_coverage(repo=repo, symbol=symbol)
        item = dict(raw)
        item["canonical_coverage_v4"] = asdict(cov)

        upstream = str(raw.get("decision_support_status") or "")
        upstream_ready = upstream == "READY_FOR_DECISION_SUPPORT"
        if upstream_ready and not cov.unresolved_blockers:
            item["decision_support_status_v4"] = "READY_FULL_DECISION_SUPPORT"
            fully_ready.append(symbol)
        elif upstream == "BLOCKED_SOURCE":
            item["decision_support_status_v4"] = "BLOCKED_SOURCE"
            coverage_blocked.append(symbol)
        else:
            item["decision_support_status_v4"] = "BLOCKED_CANONICAL_COVERAGE"
            coverage_blocked.append(symbol)

        symbols_out.append(item)

    return {
        "status": "PASS",
        "mode": "READ_ONLY_CANONICAL_INVESTABILITY_COVERAGE_BRIDGE_V4",
        "upstream_schema_version": v3_batch.get("schema_version"),
        "symbols": symbols_out,
        "summary": {
            "total_symbols": len(symbols_out),
            "ready_full_decision_support": len(fully_ready),
            "blocked_or_incomplete": len(coverage_blocked),
        },
        "ready_full_symbols": fully_ready,
        "blocked_or_incomplete_symbols": coverage_blocked,
        "production_rules": [
            "V3 output is consumed read-only; V2/V3 code is not mutated.",
            "Short-term coverage requires explicit canonical technical and market context.",
            "Long-term coverage requires explicit canonical business quality, governance and growth context.",
            "Missing, invalid or partial evidence stays blocked; it never becomes zero or PASS.",
            "No score, forecast, AL/SAT, scanner, ranking or portfolio output is created or mutated.",
            "READY_FULL_DECISION_SUPPORT is a data-coverage state, not a trade recommendation.",
        ],
        "schema_version": "fin-prod-v4-canonical-coverage-v1",
    }


def save_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
