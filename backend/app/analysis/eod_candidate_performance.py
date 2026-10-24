from __future__ import annotations
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any, Mapping

CONTRACT_ID = "EOD_CANDIDATE_PERFORMANCE_V1"
DEFAULT_ARCHIVE_PATH = Path("backend/data/eod_candidate_performance.json")
HORIZONS = (1, 3, 5)

def _as_date(value: object) -> date | None:
    try: return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError): return None

def _positive_number(value: object) -> float | None:
    try: number = float(value)
    except (TypeError, ValueError): return None
    return number if number > 0 else None

def _normalized_rows(raw_rows: Mapping[object, Mapping[str, object]]) -> dict[date, dict[str, float]]:
    result: dict[date, dict[str, float]] = {}
    for raw_date, raw in raw_rows.items():
        day = _as_date(raw_date)
        if day is None or not isinstance(raw, Mapping): continue
        values = {name: _positive_number(raw.get(name)) for name in ("high", "low", "close")}
        if any(value is None for value in values.values()): continue
        high, low, close = (float(values[key]) for key in ("high", "low", "close"))
        if high < low or not (low <= close <= high): continue
        result[day] = {"high": high, "low": low, "close": close}
    return result

def calculate_eod_candidate_performance(*, run_date: str, candidate_symbols: tuple[str, ...] | list[str], reference_prices: Mapping[str, object], price_history: Mapping[str, Mapping[object, Mapping[str, object]]]) -> dict[str, Any]:
    """Measure EOD candidates; does not select or rank candidates."""
    base_date = _as_date(run_date)
    if base_date is None: raise ValueError("RUN_DATE_INVALID")
    symbols = tuple(dict.fromkeys(str(s).strip().upper() for s in candidate_symbols if str(s).strip()))
    candidate_rows: list[dict[str, Any]] = []
    all_complete = True
    for symbol in symbols:
        base_price = _positive_number(reference_prices.get(symbol))
        rows = _normalized_rows(price_history.get(symbol, {}))
        future_dates = tuple(sorted(day for day in rows if day > base_date))
        if base_price is None:
            candidate_rows.append({"symbol": symbol, "status": "PENDING_DATA", "reason": "REFERENCE_PRICE_MISSING", "horizons": []})
            all_complete = False
            continue
        horizons: list[dict[str, Any]] = []
        for horizon in HORIZONS:
            if len(future_dates) < horizon: break
            window_dates = future_dates[:horizon]
            window = [rows[day] for day in window_dates]
            target = window[-1]
            horizons.append({"horizon": horizon, "target_date": window_dates[-1].isoformat(), "return": target["close"] / base_price - 1.0, "mfe": max(row["high"] for row in window) / base_price - 1.0, "mae": min(row["low"] for row in window) / base_price - 1.0})
        complete = len(horizons) == len(HORIZONS)
        all_complete = all_complete and complete
        candidate_rows.append({"symbol": symbol, "status": "COMPLETE" if complete else "PENDING_DATA", "reason": None if complete else "INSUFFICIENT_SESSIONS", "reference_price": base_price, "horizons": horizons})
    return {"contract_id": CONTRACT_ID, "run_date": base_date.isoformat(), "phase": "CANONICAL_CLOSE", "status": "SUCCESS" if all_complete else "PENDING_DATA", "candidate_symbols": list(symbols), "candidate_count": len(symbols), "candidates": candidate_rows}

class EodCandidatePerformanceJsonStore:
    """Separate JSON archive, idempotent by run_date and phase."""
    def __init__(self, path: Path | str = DEFAULT_ARCHIVE_PATH) -> None: self.path = Path(path)
    def load(self) -> dict[str, Any]:
        if not self.path.exists(): return {"records": []}
        try: payload = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError): return {"records": []}
        if not isinstance(payload, dict) or not isinstance(payload.get("records"), list): return {"records": []}
        return payload
    def save_record(self, record: dict[str, Any], *, recorded_at: datetime | None = None) -> dict[str, Any]:
        if record.get("contract_id") != CONTRACT_ID: raise ValueError("CONTRACT_ID_INVALID")
        if _as_date(record.get("run_date")) is None: raise ValueError("RUN_DATE_INVALID")
        payload = self.load()
        records = [item for item in payload["records"] if not (isinstance(item, dict) and item.get("contract_id") == CONTRACT_ID and item.get("run_date") == record["run_date"] and item.get("phase") == record.get("phase"))]
        saved = dict(record)
        saved["recorded_at"] = recorded_at.isoformat() if recorded_at is not None else datetime.now().astimezone().isoformat()
        records.append(saved); payload["records"] = records
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        return saved
