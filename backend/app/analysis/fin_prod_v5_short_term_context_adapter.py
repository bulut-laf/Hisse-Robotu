
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
import json

from backend.app.analysis.investability_production_closure import (
    discover_exact_canonical_candidates,
)
from backend.app.data.market_data import guvenli_fiyat_verisi_getir

try:
    from backend.app.data.bist_official_daily import yahoo_style_symbol
except Exception:
    yahoo_style_symbol = None


SCHEMA_VERSION = "fin-prod-v5-short-term-canonical-context-v7a"
MODE = "READ_ONLY_EXACT_FIRST_LEGACY_FALLBACK_V5_REV7A"

_EXACT_KEYS = {
    "technical_trend": (
        "technical_trend",
        "technical_trend_score",
        "trend_score",
        "trend_puani",
        "teknik_skor",
        "teyit_skoru",
    ),
    "relative_strength": (
        "relative_strength",
        "relative_strength_score",
        "rs_score",
        "goreceli_guc_puani",
    ),
    "volume_liquidity": (
        "volume_liquidity",
        "volume_liquidity_score",
        "liquidity_score",
        "volume_score",
        "likidite_puani",
        "hacim_birikimi_puani",
    ),
    "catalyst": (
        "catalyst",
        "catalyst_score",
    ),
    "entry_risk": (
        "entry_risk",
        "entry_risk_score",
    ),
    "earnings_surprise": (
        "earnings_surprise",
        "earnings_surprise_score",
    ),
}


_PRIORITY_ALIAS_SETS = {
    # These are distinct existing engine dimensions exposed for one adapter slot.
    # Do not merge them; take the first available existing field in tuple order.
    tuple(_EXACT_KEYS["volume_liquidity"]),
}

_DATE_KEYS = (
    "publication_date",
    "published_at",
    "as_of_date",
    "observation_date",
    "date",
)

def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value

def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    return data if isinstance(data, dict) else None

def _walk(obj: Any, path: str = "$"):
    if isinstance(obj, dict):
        yield path, obj
        for key, value in obj.items():
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from _walk(value, f"{path}[{i}]")

def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

def _date_or_none(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None

def _document_mentions_symbol(document: dict[str, Any], symbol: str) -> bool:
    target = symbol.upper()
    for _path, node in _walk(document):
        for key in ("symbol", "sembol", "ticker"):
            value = node.get(key)
            if isinstance(value, str) and value.strip().upper().replace(".IS", "") == target:
                return True
    return False

def _discover_symbol_jsons(data_root: Path, symbol: str) -> list[Path]:
    target = symbol.upper()
    own_output = f"{target}_SHORT_TERM_CANONICAL_CONTEXT.JSON"
    found: list[Path] = []
    for path in data_root.rglob("*.json"):
        name = path.name.upper()

        # Never treat this adapter's own output as input evidence.
        if name == own_output:
            continue

        if target in name:
            found.append(path)
            continue

        doc = _load_json(path)
        if doc is not None and _document_mentions_symbol(doc, target):
            found.append(path)
    return sorted(set(found))

def _extract_exact_metric(
    documents: list[tuple[str, dict[str, Any]]],
    aliases: tuple[str, ...],
) -> tuple[Decimal | None, dict[str, Any] | None]:
    priority_mode = tuple(aliases) in _PRIORITY_ALIAS_SETS

    if priority_mode:
        # Distinct existing engine dimensions mapped to one adapter slot.
        # Never average/reweight them; first available alias wins.
        for alias in aliases:
            hits: list[tuple[str, str, str, Decimal]] = []

            for source, document in documents:
                for obj_path, node in _walk(document):
                    if alias not in node:
                        continue
                    dec = _decimal_or_none(node.get(alias))
                    if dec is not None:
                        hits.append((source, obj_path, alias, dec))

            if not hits:
                continue

            unique = {hit[3] for hit in hits}
            if len(unique) != 1:
                return None, {
                    "status": "CONFLICT",
                    "alias": alias,
                    "hits": [
                        {
                            "source": h[0],
                            "object_path": h[1],
                            "key": h[2],
                            "value": str(h[3]),
                        }
                        for h in hits
                    ],
                }

            h = hits[0]
            return h[3], {
                "status": "EXACT",
                "source": h[0],
                "object_path": h[1],
                "key": h[2],
                "value": str(h[3]),
            }

        return None, None

    # Default contract: aliases are equivalent names for the SAME metric.
    # Contradictory explicit values across aliases must fail closed.
    hits: list[tuple[str, str, str, Decimal]] = []
    alias_set = set(aliases)

    for source, document in documents:
        for obj_path, node in _walk(document):
            for key, value in node.items():
                if key not in alias_set:
                    continue
                dec = _decimal_or_none(value)
                if dec is not None:
                    hits.append((source, obj_path, key, dec))

    if not hits:
        return None, None

    unique = {hit[3] for hit in hits}
    if len(unique) != 1:
        return None, {
            "status": "CONFLICT",
            "hits": [
                {
                    "source": h[0],
                    "object_path": h[1],
                    "key": h[2],
                    "value": str(h[3]),
                }
                for h in hits
            ],
        }

    h = hits[0]
    return h[3], {
        "status": "EXACT",
        "source": h[0],
        "object_path": h[1],
        "key": h[2],
        "value": str(h[3]),
    }

def _document_dates(document: dict[str, Any]) -> list[date]:
    dates: list[date] = []
    for _path, node in _walk(document):
        for key in _DATE_KEYS:
            if key in node:
                d = _date_or_none(node.get(key))
                if d is not None:
                    dates.append(d)
    return dates

def _market_symbol(symbol: str) -> str:
    if yahoo_style_symbol is not None:
        try:
            value = yahoo_style_symbol(symbol)
            if isinstance(value, str) and value.strip():
                return value.strip()
        except Exception:
            pass
    value = symbol.strip().upper()
    return value if value.endswith(".IS") else f"{value}.IS"

def _frame_index_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        ts = value.to_pydatetime()
        return ts.date()
    except Exception:
        return _date_or_none(value)

def _price_reference(
    symbol: str,
    *,
    as_of_date: date,
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    warnings: list[str] = []
    blockers: list[str] = []
    market_symbol = _market_symbol(symbol)

    try:
        recovered = guvenli_fiyat_verisi_getir(
            market_symbol,
            islem_gunu=180,
            indirme_donemi="1y",
        )
    except Exception as exc:
        return (
            None,
            [
                f"MARKET_DATA_UNAVAILABLE:{type(exc).__name__}",
                f"MARKET_SYMBOL={market_symbol}",
            ],
            blockers,
        )

    frame = getattr(recovered, "veri", recovered)
    if frame is None or getattr(frame, "empty", True):
        return None, ["MARKET_DATA_EMPTY", f"MARKET_SYMBOL={market_symbol}"], blockers

    columns = set(str(c) for c in frame.columns)
    if "Close" not in columns:
        return None, ["MARKET_DATA_CLOSE_MISSING", f"MARKET_SYMBOL={market_symbol}"], blockers

    eligible_positions: list[int] = []
    future_seen = False

    for pos, idx in enumerate(frame.index):
        d = _frame_index_date(idx)
        if d is None:
            continue
        if d <= as_of_date:
            eligible_positions.append(pos)
        else:
            future_seen = True

    if not eligible_positions:
        blockers.append("POINT_IN_TIME_PRICE_REFERENCE_MISSING")
        return None, warnings, blockers

    last_pos = eligible_positions[-1]
    row = frame.iloc[last_pos]
    idx = frame.index[last_pos]
    idx_date = _frame_index_date(idx)

    if idx_date is None or idx_date > as_of_date:
        blockers.append("POINT_IN_TIME_PRICE_VIOLATION")
        return None, warnings, blockers

    out = {
        "market_symbol": market_symbol,
        "date": idx_date.isoformat(),
        "close": str(row["Close"]),
        "point_in_time_cutoff": as_of_date.isoformat(),
    }
    if "Volume" in columns:
        out["volume"] = str(row["Volume"])

    if future_seen:
        warnings.append("FUTURE_MARKET_ROWS_EXCLUDED")

    return out, warnings, blockers


def _exact_momentum_artifact(
    *,
    data_root: Path,
    symbol: str,
    as_of_date: date,
) -> tuple[dict[str, Decimal | None], dict[str, Any], str | None]:
    path = (
        data_root
        / "financial_intelligence"
        / f"{symbol}_momentum_candidate_{as_of_date.isoformat()}.json"
    )

    document = _load_json(path)
    if document is None:
        return (
            {
                "technical_trend": None,
                "relative_strength": None,
                "volume_liquidity": None,
            },
            {
                "technical_trend": None,
                "relative_strength": None,
                "volume_liquidity": None,
            },
            None,
        )

    if str(document.get("status", "")).upper() != "PASS":
        return (
            {
                "technical_trend": None,
                "relative_strength": None,
                "volume_liquidity": None,
            },
            {
                "technical_trend": {
                    "status": "SOURCE_NOT_PASS",
                    "source": str(path),
                },
                "relative_strength": {
                    "status": "SOURCE_NOT_PASS",
                    "source": str(path),
                },
                "volume_liquidity": {
                    "status": "SOURCE_NOT_PASS",
                    "source": str(path),
                },
            },
            str(path),
        )

    document_as_of = _date_or_none(document.get("as_of_date"))
    candidate = document.get("candidate")

    if document_as_of != as_of_date or not isinstance(candidate, dict):
        return (
            {
                "technical_trend": None,
                "relative_strength": None,
                "volume_liquidity": None,
            },
            {
                "technical_trend": {
                    "status": "POINT_IN_TIME_OR_CANDIDATE_INVALID",
                    "source": str(path),
                },
                "relative_strength": {
                    "status": "POINT_IN_TIME_OR_CANDIDATE_INVALID",
                    "source": str(path),
                },
                "volume_liquidity": {
                    "status": "POINT_IN_TIME_OR_CANDIDATE_INVALID",
                    "source": str(path),
                },
            },
            str(path),
        )

    mapping = {
        "technical_trend": "trend_puani",
        "relative_strength": "goreceli_guc_puani",
        "volume_liquidity": "likidite_puani",
    }

    values: dict[str, Decimal | None] = {}
    evidence: dict[str, Any] = {}

    for target, source_key in mapping.items():
        value = _decimal_or_none(candidate.get(source_key))
        values[target] = value
        evidence[target] = (
            None
            if value is None
            else {
                "status": "EXACT_MOMENTUM_CANDIDATE_FIELD",
                "source": str(path),
                "object_path": "$.candidate",
                "key": source_key,
                "value": str(value),
            }
        )

    return values, evidence, str(path)


def build_short_term_canonical_context(
    *,
    symbol: str,
    as_of_date: date,
    data_root: str | Path,
) -> dict[str, Any]:
    symbol = str(symbol).strip().upper().replace(".IS", "")
    root = Path(data_root)

    candidates = discover_exact_canonical_candidates(root, symbol)
    paths: list[Path] = []

    for candidate in candidates:
        path_value = candidate.get("path") if isinstance(candidate, dict) else None
        if not path_value:
            continue
        p = Path(path_value)
        if not p.is_absolute():
            p = root / p
        if p.exists():
            paths.append(p)

    paths.extend(_discover_symbol_jsons(root, symbol))
    paths = sorted(set(paths))

    documents: list[tuple[str, dict[str, Any]]] = []
    for path in paths:
        doc = _load_json(path)
        if doc is not None:
            documents.append((str(path), doc))

    blockers: list[str] = []
    warnings: list[str] = []
    source_refs = [source for source, _ in documents]

    future_sources: list[str] = []
    for source, document in documents:
        dates = _document_dates(document)
        if any(d > as_of_date for d in dates):
            future_sources.append(source)

    if future_sources:
        excluded = set(future_sources)
        documents = [item for item in documents if item[0] not in excluded]
        warnings.append("FUTURE_CANONICAL_SOURCES_EXCLUDED")

    metric_values: dict[str, Decimal | None] = {}
    metric_evidence: dict[str, Any] = {}

    exact_values, exact_evidence, exact_source = _exact_momentum_artifact(
        data_root=root,
        symbol=symbol,
        as_of_date=as_of_date,
    )

    # These three fields prefer the exact producer/artifact contract.
    # If the exact historical artifact exists, generic aliases must not override it.
    # If it does not exist, retain the legacy generic canonical behavior for
    # backward compatibility and historical tests.
    for field in ("technical_trend", "relative_strength", "volume_liquidity"):
        if exact_source is not None:
            metric_values[field] = exact_values[field]
            metric_evidence[field] = exact_evidence[field]
        else:
            value, evidence = _extract_exact_metric(documents, _EXACT_KEYS[field])
            metric_values[field] = value
            metric_evidence[field] = evidence
            if evidence and evidence.get("status") == "CONFLICT":
                blockers.append(f"CONFLICTING_{field.upper()}")

    # Optional non-momentum fields retain generic exact-key discovery.
    for field in ("catalyst", "entry_risk", "earnings_surprise"):
        aliases = _EXACT_KEYS[field]
        value, evidence = _extract_exact_metric(documents, aliases)
        metric_values[field] = value
        metric_evidence[field] = evidence
        if evidence and evidence.get("status") == "CONFLICT":
            blockers.append(f"CONFLICTING_{field.upper()}")

    if exact_source is not None and exact_source not in source_refs:
        source_refs.append(exact_source)

    price_reference, price_warnings, price_blockers = _price_reference(
        symbol,
        as_of_date=as_of_date,
    )
    warnings.extend(price_warnings)
    blockers.extend(price_blockers)

    if not documents:
        blockers.append("CANONICAL_SOURCE_EVIDENCE_MISSING")
    if metric_values["technical_trend"] is None:
        blockers.append("TECHNICAL_TREND_MISSING")
    if metric_values["relative_strength"] is None:
        blockers.append("RELATIVE_STRENGTH_MISSING")
    if metric_values["volume_liquidity"] is None:
        blockers.append("VOLUME_LIQUIDITY_MISSING")

    mandatory = (
        metric_values["technical_trend"],
        metric_values["relative_strength"],
        metric_values["volume_liquidity"],
    )
    context_status = "PASS" if all(v is not None for v in mandatory) and not blockers else "BLOCKED"

    return _jsonable({
        "status": context_status,
        "mode": MODE,
        "symbol": symbol,
        "as_of_date": as_of_date.isoformat(),
        "market_context": {
            key: None if value is None else str(value)
            for key, value in metric_values.items()
        },
        "metric_evidence": metric_evidence,
        "price_reference": price_reference,
        "source_refs": source_refs,
        "excluded_future_sources": future_sources,
        "data_quality": "READY" if context_status == "PASS" else "BLOCKED_CANONICAL_COVERAGE",
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "strict_rules": [
            "No metric is guessed.",
            "Missing metrics remain null.",
            "Price reference must be on or before as_of_date.",
            "Future market rows are excluded.",
            "No AL/SAT authority.",
            "No scanner/ranking/watchlist mutation.",
            "No portfolio mutation.",
            "Future-dated evidence is excluded before metric extraction.",
            "Safely excluded future sources do not by themselves block readiness.",
            "Existing technical scores are reused exactly; no recomputation or reweighting.",
            "MomentumCandidate mapping is explicit: trend_puani / goreceli_guc_puani / likidite_puani.",
            "teknik_skor is not used as technical_trend when exact MomentumCandidate artifact exists.",
            "Legacy generic canonical fallback is used only when exact historical artifact is absent.",
        ],
        "schema_version": SCHEMA_VERSION,
    })

def save_short_term_canonical_context(payload: dict[str, Any], *, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
