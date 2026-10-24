from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "backend" / "data"
FILES = {
    "EOD_CANDIDATES": DATA / "eod_candidate_output.json",
    "EOD_PERFORMANCE": DATA / "eod_candidate_performance.json",
}

def load_json(path: Path):
    if not path.exists():
        return None, "MISSING"
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f), "OK"
    except Exception as exc:
        return None, f"ERROR: {type(exc).__name__}: {exc}"

def records_from(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("records", "items", "results", "runs", "history"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return [payload]
    return []

def first(record, *keys):
    if not isinstance(record, dict):
        return None
    for key in keys:
        if key in record:
            return record[key]
    return None

def summarize(label, path):
    payload, status = load_json(path)
    print(f"\n=== {label} ===")
    print(f"PATH: {path}")
    print(f"FILE_STATUS: {status}")
    if payload is None:
        return
    records = records_from(payload)
    print(f"RECORD_COUNT: {len(records)}")
    if not records:
        print("No records found.")
        return

    for idx, rec in enumerate(records, 1):
        if not isinstance(rec, dict):
            print(f"RECORD[{idx}]: type={type(rec).__name__}")
            continue
        run_date = first(rec, "run_date", "date", "as_of_date", "created_at")
        phase = first(rec, "phase", "run_phase")
        status_value = first(rec, "status", "state", "result")
        count = first(rec, "candidate_count", "symbol_count", "count")
        candidates = first(rec, "candidates", "candidate_symbols", "symbols", "items")
        print(f"RECORD[{idx}]: date={run_date!r} phase={phase!r} status={status_value!r} candidate_count={count!r}")
        if isinstance(candidates, list):
            print(f"  CANDIDATE_LIST_LENGTH: {len(candidates)}")
            symbols = []
            for item in candidates:
                if isinstance(item, str):
                    symbols.append(item)
                elif isinstance(item, dict):
                    sym = first(item, "symbol", "ticker", "code")
                    if sym is not None:
                        symbols.append(str(sym))
            if symbols:
                print(f"  CANDIDATE_SYMBOLS: {', '.join(symbols[:50])}")
        if label == "EOD_PERFORMANCE":
            as_of = first(rec, "evaluated_as_of", "settled_as_of", "evaluation_date")
            print(f"  EVALUATED_AS_OF: {as_of!r}")
            for k in ("complete_count", "waiting_count", "failure_count", "error_count"):
                if k in rec:
                    print(f"  {k.upper()}: {rec[k]!r}")
            if isinstance(candidates, list):
                for item in candidates[:50]:
                    if not isinstance(item, dict):
                        continue
                    symbol = first(item, "symbol", "ticker", "code")
                    state = first(item, "status", "state")
                    horizons = first(item, "horizons", "horizon_results", "performance")
                    print(f"  ITEM: symbol={symbol!r} status={state!r}")
                    if isinstance(horizons, dict):
                        for horizon, result in horizons.items():
                            if isinstance(result, dict):
                                print(f"    {horizon}: status={first(result, 'status', 'state')!r} return={first(result, 'return_pct', 'return', 'total_return')!r} date={first(result, 'target_date', 'date')!r}")
                            else:
                                print(f"    {horizon}: {result!r}")
        if idx == len(records):
            print(f"  TOP_LEVEL_KEYS: {', '.join(rec.keys())}")

def main():
    print("HISSE ROBOTU V9 — READ-ONLY OPERATIONAL CHECK")
    print("This script only reads JSON archives. It does not call APIs, fetch market data, write files, or trigger production runs.")
    print(f"CHECKED_AT: {datetime.now().isoformat(timespec='seconds')}")
    for label, path in FILES.items():
        summarize(label, path)
    print("\n=== INTERPRETATION ===")
    print("- A SUCCESS record with candidate_count=0 confirms only empty-record settlement.")
    print("- Real performance is verified only when candidate items exist and horizon results settle with actual dates/returns.")
    print("- PENDING_DATA is not a failure; it means more sessions/data are required.")
    print("- This check does not alter AL/BEKLE decisions or Top-5 ordering.")

if __name__ == "__main__":
    main()
