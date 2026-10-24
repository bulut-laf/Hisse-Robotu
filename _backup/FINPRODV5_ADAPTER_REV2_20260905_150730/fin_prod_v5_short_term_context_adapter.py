
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


SCHEMA_VERSION = "fin-prod-v5-short-term-canonical-context-v1"
MODE = "READ_ONLY_CANONICAL_SHORT_TERM_CONTEXT_ADAPTER_V5"

_EXACT_KEYS = {
    "technical_trend": (
        "technical_trend",
        "technical_trend_score",
        "trend_score",
    ),
    "relative_strength": (
        "relative_strength",
        "relative_strength_score",
        "rs_score",
    ),
    "volume_liquidity": (
        "volume_liquidity",
        "volume_liquidity_score",
        "liquidity_score",
        "volume_score",
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

def _extract_exact_metric(
    documents: list[tuple[str, dict[str, Any]]],
    aliases: tuple[str, ...],
) -> tuple[Decimal | None, dict[str, Any] | None]:
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

    # Fail closed on conflicting explicit values from multiple sources.
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

def _price_reference(symbol: str) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    try:
        recovered = guvenli_fiyat_verisi_getir(symbol, islem_gunu=60)
    except Exception as exc:
        return None, [f"MARKET_DATA_UNAVAILABLE:{type(exc).__name__}"]

    frame = getattr(recovered, "veri", recovered)
    if frame is None or getattr(frame, "empty", True):
        return None, ["MARKET_DATA_EMPTY"]

    required = {"Close"}
    columns = set(str(c) for c in frame.columns)
    if not required.issubset(columns):
        return None, ["MARKET_DATA_CLOSE_MISSING"]

    last = frame.iloc[-1]
    idx = frame.index[-1]

    out = {
        "date": str(getattr(idx, "date", lambda: idx)()),
        "close": str(last["Close"]),
    }
    if "Volume" in columns:
        out["volume"] = str(last["Volume"])

    return out, warnings

def build_short_term_canonical_context(
    *,
    symbol: str,
    as_of_date: date,
    data_root: str | Path,
) -> dict[str, Any]:
    symbol = str(symbol).strip().upper()
    root = Path(data_root)

    candidates = discover_exact_canonical_candidates(root, symbol)
    documents: list[tuple[str, dict[str, Any]]] = []

    for candidate in candidates:
        path_value = candidate.get("path") if isinstance(candidate, dict) else None
        if not path_value:
            continue
        path = Path(path_value)
        if not path.is_absolute():
            path = root / path
        doc = _load_json(path)
        if doc is not None:
            documents.append((str(path), doc))

    blockers: list[str] = []
    warnings: list[str] = []
    source_refs: list[str] = [source for source, _ in documents]

    future_sources: list[str] = []
    for source, document in documents:
        dates = _document_dates(document)
        if any(d > as_of_date for d in dates):
            future_sources.append(source)

    if future_sources:
        blockers.append("POINT_IN_TIME_VIOLATION")
        documents = [
            item for item in documents
            if item[0] not in set(future_sources)
        ]

    metric_values: dict[str, Decimal | None] = {}
    metric_evidence: dict[str, Any] = {}

    for field, aliases in _EXACT_KEYS.items():
        value, evidence = _extract_exact_metric(documents, aliases)
        metric_values[field] = value
        metric_evidence[field] = evidence
        if evidence and evidence.get("status") == "CONFLICT":
            blockers.append(f"CONFLICTING_{field.upper()}")

    price_reference, price_warnings = _price_reference(symbol)
    warnings.extend(price_warnings)

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

    payload = {
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
        "data_quality": (
            "READY"
            if context_status == "PASS"
            else "BLOCKED_CANONICAL_COVERAGE"
        ),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "strict_rules": [
            "No metric is guessed.",
            "Missing metrics remain null.",
            "No AL/SAT authority.",
            "No scanner/ranking/watchlist mutation.",
            "No portfolio mutation.",
            "Future-dated evidence is excluded.",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    return _jsonable(payload)

def save_short_term_canonical_context(
    payload: dict[str, Any],
    *,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
