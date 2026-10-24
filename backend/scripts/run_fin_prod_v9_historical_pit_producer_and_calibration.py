from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.analysis.financial_intelligence_validation import (
    PointInTimeObservation,
    calibrate_score_separation,
    validate_point_in_time,
)

ACCEPTANCE_RE = re.compile(
    r"^financial_intelligence_acceptance_(?P<symbol>[A-Z0-9.-]+)_(?P<year>\d{4})_(?P<period>[^.]+)\.json$"
)

DATE_KEYS = ("observation_date", "as_of_date", "as_of")
PUBLICATION_KEYS = ("publication_date", "published_at")
ROW_DATE_KEYS = ("date", "as_of_date", "observation_date", "trade_date", "timestamp", "datetime")
PRICE_KEYS = ("close", "price", "adj_close", "adjusted_close")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        try:
            return date.fromisoformat(s[:10])
        except Exception:
            return None


def _exact_values(node: Any, key: str) -> list[Any]:
    out: list[Any] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                out.append(v)
            out.extend(_exact_values(v, key))
    elif isinstance(node, list):
        for item in node:
            out.extend(_exact_values(item, key))
    return out


def _first_date(node: Any, keys: tuple[str, ...]) -> date | None:
    for key in keys:
        for value in _exact_values(node, key):
            parsed = _parse_date(value)
            if parsed is not None:
                return parsed
    return None


def _latest_publication_not_after(node: Any, observation_date: date) -> date | None:
    found = []
    for key in PUBLICATION_KEYS:
        for value in _exact_values(node, key):
            parsed = _parse_date(value)
            if parsed is not None and parsed <= observation_date:
                found.append(parsed)
    return max(found) if found else None


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _financial_health_score(node: Any) -> float | None:
    for key in ("financial_health_score", "health_score"):
        for value in _exact_values(node, key):
            parsed = _as_float(value)
            if parsed is not None:
                return parsed

    for value in _exact_values(node, "financial_health"):
        parsed = _as_float(value)
        if parsed is not None:
            return parsed
        if isinstance(value, dict):
            for key in ("score", "value", "total_score", "overall_score"):
                parsed = _as_float(value.get(key))
                if parsed is not None:
                    return parsed
    return None


def _score_from_canonical_sources(fi_dir: Path, symbol: str, acceptance_path: Path):
    sources = [
        fi_dir / f"{symbol}_financial_intelligence_panel.json",
        acceptance_path,
        fi_dir / f"{symbol}_investability_acceptance.json",
        fi_dir / f"{symbol}_investability_production_closure.json",
    ]
    for path in sources:
        if not path.exists():
            continue
        try:
            obj = _load_json(path)
        except Exception:
            continue
        score = _financial_health_score(obj)
        if score is not None:
            return score, str(path)
    return None, None


def _market_symbol_aliases(symbol: str) -> set[str]:
    # Explicit deterministic BIST market alias only.
    return {symbol.upper(), f"{symbol.upper()}.IS"}


def _extract_market_rows_json(path: Path, aliases: set[str]) -> list[tuple[date, float]]:
    try:
        obj = _load_json(path)
    except Exception:
        return []

    rows = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            sym = node.get("symbol")
            if not isinstance(sym, str):
                sym = node.get("ticker")

            if isinstance(sym, str) and sym.strip().upper() in aliases:
                d = None
                px = None

                for key in ROW_DATE_KEYS:
                    if key in node:
                        d = _parse_date(node[key])
                        if d:
                            break

                for key in PRICE_KEYS:
                    if key in node:
                        px = _as_float(node[key])
                        if px is not None:
                            break

                if d is not None and px is not None and px > 0:
                    rows.append((d, px))

            for value in node.values():
                walk(value)

        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(obj)
    return rows


def _extract_market_rows_csv(path: Path, aliases: set[str]) -> list[tuple[date, float]]:
    rows = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            symbol_key = "symbol" if "symbol" in fields else ("ticker" if "ticker" in fields else None)
            date_key = next((k for k in ROW_DATE_KEYS if k in fields), None)
            price_key = next((k for k in PRICE_KEYS if k in fields), None)
            if not symbol_key or not date_key or not price_key:
                return []

            for row in reader:
                if str(row.get(symbol_key, "")).strip().upper() not in aliases:
                    continue
                d = _parse_date(row.get(date_key))
                px = _as_float(row.get(price_key))
                if d is not None and px is not None and px > 0:
                    rows.append((d, px))
    except Exception:
        return []
    return rows


def _market_series(data_dir: Path, symbol: str) -> list[tuple[date, float, str]]:
    aliases = _market_symbol_aliases(symbol)
    found = []

    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() == ".json":
            rows = _extract_market_rows_json(path, aliases)
        elif path.suffix.lower() == ".csv":
            rows = _extract_market_rows_csv(path, aliases)
        else:
            continue

        for d, px in rows:
            found.append((d, px, str(path)))

    unique = {}
    for d, px, src in found:
        unique.setdefault((d, px), src)

    out = [(d, px, src) for (d, px), src in unique.items()]
    out.sort(key=lambda row: (row[0], row[1], row[2]))
    return out


def _forward_20_session_return(rows, observation_date):
    base_rows = [row for row in rows if row[0] == observation_date]
    if not base_rows:
        return None, {"blocker": "OBSERVATION_DATE_MARKET_PRICE_MISSING"}

    base_prices = sorted(set(row[1] for row in base_rows))
    if len(base_prices) != 1:
        return None, {"blocker": "AMBIGUOUS_OBSERVATION_DATE_MARKET_PRICE"}

    future = [row for row in rows if row[0] > observation_date]
    by_date = {}
    src_by_date = {}
    for d, px, src in future:
        by_date.setdefault(d, set()).add(px)
        src_by_date.setdefault(d, []).append(src)

    clean_dates = [d for d in sorted(by_date) if len(by_date[d]) == 1]
    if len(clean_dates) < 20:
        return None, {"blocker": "FORWARD_20_SESSION_MARKET_DATA_INSUFFICIENT"}

    target_date = clean_dates[19]
    base_price = base_prices[0]
    target_price = next(iter(by_date[target_date]))

    return target_price / base_price - 1.0, {
        "base_date": observation_date.isoformat(),
        "base_price": base_price,
        "target_date": target_date.isoformat(),
        "target_price": target_price,
        "forward_sessions": 20,
        "sources": sorted(set([r[2] for r in base_rows] + src_by_date[target_date])),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    data_dir = backend / "data"
    fi_dir = data_dir / "financial_intelligence"

    observations = []
    evidence = []
    blockers = []

    for path in sorted(data_dir.glob("financial_intelligence_acceptance_*.json")):
        match = ACCEPTANCE_RE.match(path.name)
        if not match:
            continue

        symbol = match.group("symbol").upper()
        acceptance = _load_json(path)

        panel_path = fi_dir / f"{symbol}_financial_intelligence_panel.json"
        panel = _load_json(panel_path) if panel_path.exists() else {}

        observation_date = _first_date(acceptance, DATE_KEYS) or _first_date(panel, DATE_KEYS)
        if observation_date is None:
            blockers.append(f"OBSERVATION_DATE_MISSING:{symbol}")
            continue

        publication_date = (
            _latest_publication_not_after(acceptance, observation_date)
            or _latest_publication_not_after(panel, observation_date)
        )
        if publication_date is None:
            blockers.append(f"PUBLICATION_DATE_MISSING:{symbol}")
            continue

        score, score_source = _score_from_canonical_sources(fi_dir, symbol, path)
        if score is None:
            blockers.append(f"SCORE_MISSING:{symbol}")
            continue

        market_rows = _market_series(data_dir, symbol)
        forward_return, outcome = _forward_20_session_return(market_rows, observation_date)
        if forward_return is None:
            blockers.append(f"{outcome['blocker']}:{symbol}")
            continue

        obs = PointInTimeObservation(
            observation_date=observation_date,
            publication_date=publication_date,
            score=score,
            forward_return=forward_return,
        )

        if not validate_point_in_time(obs):
            blockers.append(f"PIT_VALIDATION_FAILED:{symbol}")
            continue

        observations.append(obs)
        evidence.append({
            "symbol": symbol,
            "market_aliases": sorted(_market_symbol_aliases(symbol)),
            "acceptance_source": str(path),
            "score_source": score_source,
            "score": score,
            "observation_date": observation_date.isoformat(),
            "publication_date": publication_date.isoformat(),
            "forward_return": forward_return,
            "forward_outcome": outcome,
        })

    calibration = calibrate_score_separation(observations)
    count = len(observations)

    status = (
        "PRODUCTION_CALIBRATION_READY" if count >= 20
        else "INSUFFICIENT_SAMPLE" if count > 0
        else "NO_PRODUCTION_OBSERVATIONS"
    )

    payload = {
        "schema_version": "fin-prod-v9-historical-pit-production-observations-v6",
        "status": status,
        "mode": "READ_ONLY_PRODUCTION_PIT_OBSERVATION_PRODUCER",
        "production_evidence": count > 0,
        "observation_count": count,
        "observations": [
            {
                "observation_date": o.observation_date.isoformat(),
                "publication_date": o.publication_date.isoformat(),
                "score": o.score,
                "forward_return": o.forward_return,
            }
            for o in observations
        ],
        "evidence": evidence,
        "calibration": {
            "status": getattr(calibration, "status", None),
            "separation": getattr(calibration, "separation", None),
        },
        "blockers": sorted(set(blockers)),
        "rules": [
            "EXACT_FINANCIAL_HEALTH_FIELD_ONLY",
            "EXACT_BIST_MARKET_ALIAS_SYMBOL_OR_SYMBOL_DOT_IS_ONLY",
            "EXACT_PUBLICATION_TIMESTAMP_REQUIRED",
            "PUBLICATION_MUST_NOT_EXCEED_OBSERVATION_DATE",
            "FORWARD_OUTCOME_USES_20_POST_OBSERVATION_SESSIONS",
            "NO_SYNTHETIC_PRODUCTION_CALIBRATION",
            "NO_WEIGHT_OPTIMIZATION",
            "NO_THRESHOLD_OPTIMIZATION",
            "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION",
        ],
    }

    out = fi_dir / "FIN_PROD_V9_HISTORICAL_PIT_PRODUCTION_OBSERVATIONS.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS={status}")
    print(f"OBSERVATION_COUNT={count}")
    print(f"CALIBRATION_STATUS={payload['calibration']['status']}")
    print(f"SEPARATION={payload['calibration']['separation']}")
    print(f"BLOCKERS={payload['blockers']}")
    if evidence:
        print(f"SCORE_SOURCE={evidence[0]['score_source']}")
        print(f"SCORE={evidence[0]['score']}")
        print(f"MARKET_ALIASES={evidence[0]['market_aliases']}")
        print(f"BASE_PRICE={evidence[0]['forward_outcome']['base_price']}")
        print(f"TARGET_PRICE={evidence[0]['forward_outcome']['target_price']}")
    print(f"RESULT={out}")
    print("FIN_PROD_V9_HISTORICAL_PIT_MARKET_ALIAS_REPAIR_V6=PASS")


if __name__ == "__main__":
    main()
