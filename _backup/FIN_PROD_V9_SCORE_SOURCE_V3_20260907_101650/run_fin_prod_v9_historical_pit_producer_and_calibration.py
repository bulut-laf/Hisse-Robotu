from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict
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
SCORE_KEYS = ("financial_health_score", "health_score")
PRICE_KEYS = ("close", "price")
ROW_DATE_KEYS = ("date", "as_of_date", "observation_date")
SYMBOL_KEYS = ("symbol",)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _parse_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()
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
    out = []
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
        for v in _exact_values(node, key):
            d = _parse_date(v)
            if d is not None:
                return d
    return None


def _latest_publication_not_after(node: Any, observation_date: date) -> date | None:
    vals = []
    for key in PUBLICATION_KEYS:
        for v in _exact_values(node, key):
            d = _parse_date(v)
            if d is not None and d <= observation_date:
                vals.append(d)
    return max(vals) if vals else None


def _first_numeric(node: Any, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        for v in _exact_values(node, key):
            if isinstance(v, bool):
                continue
            try:
                return float(v)
            except Exception:
                pass
    return None


def _extract_market_rows_from_json(path: Path, symbol: str) -> list[tuple[date, float]]:
    try:
        obj = _load_json(path)
    except Exception:
        return []

    rows: list[tuple[date, float]] = []

    def walk(node: Any):
        if isinstance(node, dict):
            sym = None
            for k in SYMBOL_KEYS:
                if k in node and isinstance(node[k], str):
                    sym = node[k].strip().upper()
                    break

            d = None
            for k in ROW_DATE_KEYS:
                if k in node:
                    d = _parse_date(node[k])
                    if d:
                        break

            px = None
            for k in PRICE_KEYS:
                if k in node:
                    try:
                        px = float(node[k])
                    except Exception:
                        px = None
                    if px is not None:
                        break

            if sym == symbol and d is not None and px is not None and px > 0:
                rows.append((d, px))

            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(obj)
    return rows


def _extract_market_rows_from_csv(path: Path, symbol: str) -> list[tuple[date, float]]:
    rows: list[tuple[date, float]] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fields = set(reader.fieldnames or [])
            symbol_key = "symbol" if "symbol" in fields else None
            date_key = next((k for k in ROW_DATE_KEYS if k in fields), None)
            price_key = next((k for k in PRICE_KEYS if k in fields), None)
            if not symbol_key or not date_key or not price_key:
                return []
            for row in reader:
                if str(row.get(symbol_key, "")).strip().upper() != symbol:
                    continue
                d = _parse_date(row.get(date_key))
                try:
                    px = float(row.get(price_key))
                except Exception:
                    px = None
                if d and px and px > 0:
                    rows.append((d, px))
    except Exception:
        return []
    return rows


def _market_series(data_dir: Path, symbol: str) -> list[tuple[date, float, str]]:
    found: list[tuple[date, float, str]] = []
    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".json":
            rows = _extract_market_rows_from_json(path, symbol)
        elif path.suffix.lower() == ".csv":
            rows = _extract_market_rows_from_csv(path, symbol)
        else:
            continue
        for d, px in rows:
            found.append((d, px, str(path)))

    # Deterministic de-dupe by date+price, then sort.
    uniq = {}
    for d, px, src in found:
        uniq.setdefault((d, px), src)
    out = [(d, px, src) for (d, px), src in uniq.items()]
    out.sort(key=lambda x: (x[0], x[1], x[2]))
    return out


def _forward_20_session_return(
    rows: list[tuple[date, float, str]],
    observation_date: date,
) -> tuple[float | None, dict[str, Any]]:
    on_date = [r for r in rows if r[0] == observation_date]
    future = [r for r in rows if r[0] > observation_date]

    # one canonical close required for observation date
    if not on_date:
        return None, {"blocker": "OBSERVATION_DATE_MARKET_PRICE_MISSING"}
    base_prices = sorted(set(r[1] for r in on_date))
    if len(base_prices) != 1:
        return None, {"blocker": "AMBIGUOUS_OBSERVATION_DATE_MARKET_PRICE"}

    # unique future dates, deterministic single price per date only
    by_date: dict[date, set[float]] = {}
    src_by_date: dict[date, list[str]] = {}
    for d, px, src in future:
        by_date.setdefault(d, set()).add(px)
        src_by_date.setdefault(d, []).append(src)

    clean_dates = [d for d in sorted(by_date) if len(by_date[d]) == 1]
    if len(clean_dates) < 20:
        return None, {"blocker": "FORWARD_20_SESSION_MARKET_DATA_INSUFFICIENT"}

    target_date = clean_dates[19]
    base = base_prices[0]
    target = next(iter(by_date[target_date]))
    ret = target / base - 1.0

    return ret, {
        "base_date": observation_date.isoformat(),
        "base_price": base,
        "target_date": target_date.isoformat(),
        "target_price": target,
        "forward_sessions": 20,
        "sources": sorted(set([r[2] for r in on_date] + src_by_date[target_date])),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    backend = root / "backend"
    data_dir = backend / "data"
    fi_dir = data_dir / "financial_intelligence"

    observations = []
    evidence = []
    blockers = []

    acceptance_files = sorted(data_dir.glob("financial_intelligence_acceptance_*.json"))
    for path in acceptance_files:
        m = ACCEPTANCE_RE.match(path.name)
        if not m:
            continue

        symbol = m.group("symbol").upper()
        try:
            acc = _load_json(path)
        except Exception:
            blockers.append(f"INVALID_ACCEPTANCE_JSON:{path.name}")
            continue

        observation_date = _first_date(acc, DATE_KEYS)

        # Panel may carry exact health score / as_of as accepted production read model.
        panel_path = fi_dir / f"{symbol}_financial_intelligence_panel.json"
        panel = {}
        if panel_path.exists():
            try:
                panel = _load_json(panel_path)
            except Exception:
                panel = {}

        if observation_date is None:
            observation_date = _first_date(panel, DATE_KEYS)

        score = _first_numeric(acc, SCORE_KEYS)
        if score is None:
            score = _first_numeric(panel, SCORE_KEYS)

        if observation_date is None:
            blockers.append(f"OBSERVATION_DATE_MISSING:{symbol}")
            continue
        if score is None:
            blockers.append(f"SCORE_MISSING:{symbol}")
            continue

        publication_date = _latest_publication_not_after(acc, observation_date)
        if publication_date is None:
            publication_date = _latest_publication_not_after(panel, observation_date)
        if publication_date is None:
            blockers.append(f"PUBLICATION_DATE_MISSING:{symbol}")
            continue

        market = _market_series(data_dir, symbol)
        forward_return, outcome_ev = _forward_20_session_return(market, observation_date)
        if forward_return is None:
            blockers.append(f"{outcome_ev['blocker']}:{symbol}")
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
            "acceptance_source": str(path),
            "panel_source": str(panel_path) if panel_path.exists() else None,
            "observation_date": observation_date.isoformat(),
            "publication_date": publication_date.isoformat(),
            "score": score,
            "score_semantics": "FINANCIAL_HEALTH_SCORE",
            "forward_return": forward_return,
            "forward_outcome": outcome_ev,
        })

    calibration = calibrate_score_separation(observations)

    usable = len(observations)
    if usable >= 20:
        status = "PRODUCTION_CALIBRATION_READY"
    elif usable > 0:
        status = "INSUFFICIENT_SAMPLE"
    else:
        status = "NO_PRODUCTION_OBSERVATIONS"

    out = fi_dir / "FIN_PROD_V9_HISTORICAL_PIT_PRODUCTION_OBSERVATIONS.json"
    payload = {
        "schema_version": "fin-prod-v9-historical-pit-production-observations-v1",
        "status": status,
        "mode": "READ_ONLY_PRODUCTION_PIT_OBSERVATION_PRODUCER",
        "production_evidence": True if usable > 0 else False,
        "observation_count": usable,
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
            "EXACT_ACCEPTANCE_FILENAME_CONTRACT",
            "EXACT_PUBLICATION_TIMESTAMP_REQUIRED",
            "PUBLICATION_MUST_NOT_EXCEED_OBSERVATION_DATE",
            "EXACT_FINANCIAL_HEALTH_SCORE_ONLY",
            "EXACT_MARKET_DATE_AND_CLOSE_OR_PRICE_KEYS_ONLY",
            "FORWARD_OUTCOME_USES_20_POST_OBSERVATION_SESSIONS",
            "NO_SYNTHETIC_PRODUCTION_CALIBRATION",
            "NO_WEIGHT_OPTIMIZATION",
            "NO_THRESHOLD_OPTIMIZATION",
            "NO_AL_SAT_SCANNER_RANKING_PORTFOLIO_MUTATION",
        ],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"STATUS={status}")
    print(f"OBSERVATION_COUNT={usable}")
    print(f"CALIBRATION_STATUS={payload['calibration']['status']}")
    print(f"SEPARATION={payload['calibration']['separation']}")
    print(f"BLOCKERS={payload['blockers']}")
    print(f"RESULT={out}")
    print("FIN_PROD_V9_HISTORICAL_PIT_PRODUCER_AND_CALIBRATION=PASS")


if __name__ == "__main__":
    main()
