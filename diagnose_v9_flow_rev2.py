from __future__ import annotations

import ast
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
SEARCH_ROOTS = [ROOT / "backend", ROOT / "scripts", ROOT]
SKIP_DIRS = {".venv", ".git", "__pycache__", "node_modules", ".pytest_cache"}
NAME_TARGETS = {
    "daily_buy_decision_scheduled_runner.py",
    "scheduled_operation_phase_runner.py",
    "scheduled_intraday_batch.py",
    "eod_candidate_performance_runtime.py",
}
TOKENS = (
    "ProductionScheduledOperationRuntime",
    "execute_scheduled_run",
    "canonical_close(",
    "scheduled_operation_phase_runner",
    "daily_buy_decision_scheduled_runner",
    "EOD_V9C_REV1_PERFORMANCE_HISTORY_HOOK",
    "settle_eod_candidate_performance_history",
    "run_scheduled_operation",
    "scheduled_operation",
    "CANONICAL_CLOSE",
)

def iter_files():
    seen = set()
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(ROOT)
            except ValueError:
                continue
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            if path.suffix.lower() not in {".py", ".ps1", ".bat", ".cmd", ".json", ".yml", ".yaml", ".toml"}:
                continue
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            yield path

def excerpt(path: Path, lines: list[str], lo: int, hi: int):
    print(f"\n--- {path.relative_to(ROOT)} lines {lo}-{hi} ---")
    for n in range(max(1, lo), min(len(lines), hi) + 1):
        print(f"{n:4}: {lines[n-1][:260]}")

def main():
    print("HISSE ROBOTU V9 — FLOW DIAGNOSTIC REV2 (READ ONLY)")
    print("No network, no market-data fetch, no archive writes, no production run.")
    print(f"CHECKED_AT: {datetime.now().isoformat(timespec='seconds')}")
    print(f"ROOT: {ROOT}")

    files = list(iter_files())
    print("\n=== EXACT FILE DISCOVERY ===")
    for p in files:
        if p.name in NAME_TARGETS:
            print(f"FOUND: {p.relative_to(ROOT)}")
    missing = [name for name in sorted(NAME_TARGETS) if not any(p.name == name for p in files)]
    for name in missing:
        print(f"NOT_FOUND: {name}")

    print("\n=== ENTRYPOINT / SCHEDULER FILE CANDIDATES ===")
    candidates = []
    for p in files:
        low = str(p.relative_to(ROOT)).lower()
        if any(x in low for x in ("schedule", "runner", "operation", "cron", "task", "daily_buy_decision")):
            candidates.append(p)
    for p in candidates[:120]:
        print(f"FILE: {p.relative_to(ROOT)}")

    print("\n=== RELEVANT SOURCE EXCERPTS ===")
    for p in files:
        if p.name not in NAME_TARGETS and p not in candidates:
            continue
        try:
            text = p.read_text(encoding="utf-8-sig")
        except Exception:
            continue
        lines = text.splitlines()
        try:
            ast.parse(text) if p.suffix == ".py" else None
            syntax = "OK"
        except SyntaxError as exc:
            syntax = f"ERROR line {exc.lineno}: {exc.msg}"
        print(f"\nFILE_STATUS: {p.relative_to(ROOT)} | lines={len(lines)} | syntax={syntax}")
        matched = [i for i, line in enumerate(lines, 1) if any(tok in line for tok in TOKENS)]
        if p.name == "scheduled_operation_phase_runner.py":
            windows = []
            for i in matched:
                windows.append((max(1, i-5), min(len(lines), i+10)))
            # Include canonical runtime method region when present.
            for i, line in enumerate(lines, 1):
                if "class ProductionScheduledOperationRuntime" in line:
                    windows.append((i, min(len(lines), i+90)))
            merged = []
            for lo, hi in sorted(windows):
                if merged and lo <= merged[-1][1] + 2:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
                else:
                    merged.append((lo, hi))
            for lo, hi in merged[:15]:
                excerpt(p, lines, lo, hi)
        else:
            for i in matched[:25]:
                excerpt(p, lines, max(1, i-3), min(len(lines), i+5))

    print("\n=== SAFE INTERPRETATION ===")
    print("- A source file's presence or marker does not prove scheduled execution.")
    print("- Missing expected filename is not proof the module is absent; use FOUND paths and import excerpts.")
    print("- This diagnostic never imports or executes project modules.")
    print("- No production decisions, candidate ordering, or archives are modified.")

if __name__ == "__main__":
    main()
