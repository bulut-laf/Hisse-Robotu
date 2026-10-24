param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu",
    [string]$ReportPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$MarketScanner = Join-Path $ProjectRoot "backend\app\analysis\market_scanner.py"
$MemoryFile = Join-Path $ProjectRoot "data\ranking_memory\rank_observations.jsonl"
$Discovery = Join-Path $ProjectRoot "_discovery"

foreach ($p in @($Python, $MarketScanner, $MemoryFile)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

if ([string]::IsNullOrWhiteSpace($ReportPath)) {
    $candidate = Get-ChildItem -LiteralPath $Discovery `
        -Filter "Hisse-Robotu-Daily10-Ranking-Memory-Backfill-V1-*.txt" `
        -File `
        | Sort-Object LastWriteTime -Descending `
        | Select-Object -First 1

    if ($null -eq $candidate) {
        throw "LATEST_BACKFILL_REPORT_NOT_FOUND"
    }

    $ReportPath = $candidate.FullName
}

if (-not (Test-Path -LiteralPath $ReportPath)) {
    throw "REPORT_NOT_FOUND=$ReportPath"
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_backfill_rootcause_diagnostic_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — DAILY10 BACKFILL ROOT-CAUSE DIAGNOSTIC V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host ("REPORT=" + $ReportPath)

    Write-Host ""
    Write-Host "=== FAILURE EVIDENCE FROM REPORT ==="

    $lines = @(Get-Content -LiteralPath $ReportPath -Encoding UTF8)
    $interesting = $lines | Where-Object {
        $_ -match "25-AUG CONTRACT PARITY" -or
        $_ -match "^SOURCE=" -or
        $_ -match "EXACT_25AUG" -or
        $_ -match "BACKFILL_CONTRACT_BLOCKED" -or
        $_ -match "BACKFILL_BLOCKED" -or
        $_ -match "BACKFILL_POSTWRITE_FAIL" -or
        $_ -match "^Traceback" -or
        $_ -match "^RuntimeError" -or
        $_ -match "^ValueError" -or
        $_ -match "^TypeError" -or
        $_ -match "CROSS_CONTRACT" -or
        $_ -match "KEY_CONFLICT"
    }

    if (@($interesting).Count -eq 0) {
        Write-Host "REPORT_INTERESTING_LINES=NONE"
        Write-Host "REPORT_LAST_80_LINES:"
        $lines | Select-Object -Last 80 | ForEach-Object { Write-Host $_ }
    }
    else {
        $interesting | ForEach-Object { Write-Host $_ }
    }

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

root = Path(sys.argv[1])
market_path = root / "backend/app/analysis/market_scanner.py"
memory_path = root / "data/ranking_memory/rank_observations.jsonl"

market = market_path.read_text(encoding="utf-8", errors="replace")

print()
print("=== CURRENT MARKET SCANNER SNAPSHOT HOOK ===")

slice_patterns = (
    r"adaylar\s*=\s*tuple\s*\(\s*filtrelenmis\.adaylar\s*\[\s*:\s*istek\.maksimum_aday\s*\]\s*\)",
    r"adaylar\s*=\s*tuple\s*\(\s*filtrelenmis\.adaylar\s*\[\s*:\s*.*maksimum_aday.*\]\s*\)",
)
display_slice = any(re.search(p, market, flags=re.S) for p in slice_patterns)

persist_match = re.search(
    r"persist_research_rank_snapshot\s*\((?P<body>[\s\S]{0,1200}?)\n\s*\)",
    market,
)
persist_body = persist_match.group("body") if persist_match else ""

persists_display = bool(
    persist_body
    and re.search(r"for\s+sira\s*,\s*aday\s+in\s+enumerate\s*\(\s*adaylar\s*,", persist_body)
)
persists_full = bool(
    persist_body
    and re.search(
        r"for\s+sira\s*,\s*aday\s+in\s+enumerate\s*\(\s*filtrelenmis\.adaylar\s*,",
        persist_body,
    )
)

print(f"DISPLAY_SLICE_DEFINED={'YES' if display_slice else 'NO'}")
print(f"PERSIST_HOOK_PRESENT={'YES' if bool(persist_match) else 'NO'}")
print(f"PERSIST_ENUMERATES_DISPLAY_ADAYLAR={'YES' if persists_display else 'NO'}")
print(f"PERSIST_ENUMERATES_FULL_FILTERED={'YES' if persists_full else 'NO'}")

if persist_match:
    compact = " ".join(persist_body.split())
    print("PERSIST_HOOK_COMPACT=" + compact[:900])

print()
print("=== 25-AUG RANKING MEMORY GROUPS ===")

def parse_date(raw: str):
    value = str(raw or "").strip()
    for parser in (
        lambda x: date.fromisoformat(x),
        lambda x: date(
            int(x.split("/")[2]),
            int(x.split("/")[1]),
            int(x.split("/")[0]),
        ),
    ):
        try:
            return parser(value)
        except (ValueError, IndexError):
            continue
    return None

items = []
for raw in memory_path.read_text(encoding="utf-8").splitlines():
    raw = raw.strip()
    if raw:
        items.append(json.loads(raw))

target = date(2026, 8, 25)
groups = defaultdict(list)

for item in items:
    if parse_date(item.get("as_of", "")) == target:
        groups[(item.get("universe_source", ""), item.get("profile_name", ""))].append(item)

print(f"GROUP_COUNT={len(groups)}")

for (source, profile), rows in sorted(
    groups.items(),
    key=lambda pair: (-len(pair[1]), str(pair[0][0]), str(pair[0][1])),
):
    ranks = sorted(int(x["rank"]) for x in rows)
    sizes = sorted({int(x["ranked_universe_size"]) for x in rows})
    contiguous = ranks == list(range(1, len(ranks) + 1))
    encoded_as_slice = (
        len(sizes) == 1
        and sizes[0] == len(rows)
        and contiguous
    )

    print(
        f"SOURCE={source!r} PROFILE={profile!r} "
        f"ROWS={len(rows)} MIN_RANK={min(ranks) if ranks else '-'} "
        f"MAX_RANK={max(ranks) if ranks else '-'} "
        f"UNIVERSE_SIZES={sizes} "
        f"CONTIGUOUS_1_TO_N={'YES' if contiguous else 'NO'} "
        f"ENCODED_UNIVERSE_EQUALS_ROW_COUNT={'YES' if encoded_as_slice else 'NO'}"
    )

print()
print("=== FINAL ROOT-CAUSE CLASSIFICATION ===")

if display_slice and persists_display and not persists_full:
    print("ROOT_CAUSE=RANKING_MEMORY_CAPTURE_USES_DISPLAY_SLICE_NOT_FULL_FILTERED_RESEARCH")
    print(
        "IMPACT=ranked_universe_size_is_derived_from_display_row_count;"
        "historical_full_replay_cannot_be_rank_for_rank_equal_to_existing_snapshot"
    )
    print(
        "NEXT=DO_NOT_BACKFILL_YET;"
        "PATCH_SNAPSHOT_HOOK_TO_PERSIST_FULL_FILTERED_RESEARCH;"
        "THEN_VALIDATE_AND_REBUILD_AFFECTED_SESSION_SNAPSHOTS"
    )
elif persists_full:
    print("ROOT_CAUSE=NOT_DISPLAY_SLICE_CAPTURE")
    print("NEXT=USE_REPORT_RUNTIME_ERROR_AS_PRIMARY_FAILURE_CAUSE")
else:
    print("ROOT_CAUSE=SNAPSHOT_HOOK_CONTRACT_NOT_PROVEN_FROM_CURRENT_SOURCE")
    print("NEXT=INSPECT_CURRENT_HOOK_AND_REPORT_BEFORE_ANY_MUTATION")

print("BACKFILL_ROOTCAUSE_DIAGNOSTIC=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "BACKFILL_ROOTCAUSE_DIAGNOSTIC_FAIL"
    }
}
finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue

    if ($null -eq $oldPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $oldPythonPath
    }
}
