from __future__ import annotations

import ast
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
APP = ROOT / "backend" / "app"
DATA = ROOT / "backend" / "data"

TARGETS = [
    APP / "operations" / "scheduled_operation_phase_runner.py",
    APP / "analysis" / "daily_buy_decision_scheduled_runner.py",
    APP / "analysis" / "eod_candidate_performance_runtime.py",
]

ARCHIVES = [
    DATA / "eod_candidate_output.json",
    DATA / "eod_candidate_performance.json",
]

TOKENS = (
    "canonical_close",
    "execute_scheduled_run",
    "EodCandidateOutputJsonStore",
    "settle_eod_candidate_performance_history",
    "EOD_V9C_REV1_PERFORMANCE_HISTORY_HOOK",
    "NO_CANDIDATES",
    "candidate_symbols",
    "run_scheduled_intraday_batch",
)

def print_source_summary(path: Path) -> None:
    print(f"\n=== SOURCE: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path} ===")
    if not path.exists():
        print("SOURCE_STATUS: MISSING")
        return
    print("SOURCE_STATUS: OK")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except Exception as exc:
        print(f"READ_ERROR: {type(exc).__name__}: {exc}")
        return
    print(f"LINE_COUNT: {len(text.splitlines())}")
    try:
        ast.parse(text)
        print("PYTHON_SYNTAX: OK")
    except SyntaxError as exc:
        print(f"PYTHON_SYNTAX: ERROR line={exc.lineno} message={exc.msg}")
    lines = text.splitlines()
    hits = []
    for i, line in enumerate(lines, 1):
        if any(token in line for token in TOKENS):
            hits.append((i, line.strip()))
    if not hits:
        print("RELEVANT_MARKERS: NONE")
    else:
        print("RELEVANT_MARKERS:")
        for line_no, line in hits[:100]:
            print(f"  L{line_no}: {line[:240]}")

def load_json(path: Path):
    if not path.exists():
        return None, "MISSING"
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            return json.load(f), "OK"
    except Exception as exc:
        return None, f"ERROR {type(exc).__name__}: {exc}"

def summarize_archive(path: Path) -> None:
    print(f"\n=== ARCHIVE: {path.relative_to(ROOT)} ===")
    payload, status = load_json(path)
    print(f"FILE_STATUS: {status}")
    if payload is None:
        return
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = next((payload[k] for k in ("records", "items", "results", "runs", "history") if isinstance(payload.get(k), list)), [payload])
    else:
        records = []
    print(f"RECORD_COUNT: {len(records)}")
    for i, record in enumerate(records[-10:], 1):
        if not isinstance(record, dict):
            print(f"RECORD[{i}]: non-object {type(record).__name__}")
            continue
        print(
            f"RECORD[{i}]: run_date={record.get('run_date')!r} "
            f"created_at={record.get('created_at', record.get('recorded_at'))!r} "
            f"phase={record.get('phase')!r} status={record.get('status')!r} "
            f"candidate_count={record.get('candidate_count')!r} "
            f"candidate_symbols={record.get('candidate_symbols')!r}"
        )

def main():
    print("HISSE ROBOTU V9 — READ-ONLY FLOW DIAGNOSTIC")
    print("No network, no market-data fetch, no archive writes, no production run.")
    print(f"CHECKED_AT: {datetime.now().isoformat(timespec='seconds')}")
    print(f"PROJECT_ROOT: {ROOT}")
    for path in TARGETS:
        print_source_summary(path)
    for path in ARCHIVES:
        summarize_archive(path)
    print("\n=== SAFETY ===")
    print("This diagnostic only reads source files and JSON archives.")
    print("It does not invoke scheduled runners or change AL/BEKLE / Top-5.")
    print("Interpret source markers together with runtime logs; marker presence alone does not prove a run occurred.")

if __name__ == "__main__":
    main()
