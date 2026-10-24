param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Memory = Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py"
$Trajectory = Join-Path $ProjectRoot "backend\app\analysis\ranking_trajectory.py"

foreach ($p in @($Python,$Memory,$Trajectory)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$oldPythonPath = $env:PYTHONPATH
$tmp = Join-Path $env:TEMP "hisse_daily10_trajectory_diagnostic_v1.py"

try {
    Write-Host "=== HISSE ROBOTU — DAILY10 TRAJECTORY DIAGNOSTIC V1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "PRODUCTION_MUTATION=NO"
    Write-Host "GOAL=WHY_HEALTHY_EARLY_NONE"

    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($oldPythonPath)) {
        $ProjectRoot
    } else {
        "$ProjectRoot;$oldPythonPath"
    }

    $code = @'
from collections import Counter, defaultdict
from backend.app.analysis.ranking_memory import RankObservationJsonlStore
from backend.app.analysis.ranking_trajectory import build_rank_trajectories

store = RankObservationJsonlStore()
history = store.list()
trajectories = build_rank_trajectories(history)

dates = sorted({item.as_of for item in history})
symbols = sorted({item.symbol for item in history})

print(f"STORE_PATH={store.path}")
print(f"RANK_OBSERVATIONS={len(history)}")
print(f"UNIQUE_DATES={len(dates)}")
print(f"DATE_RANGE={(dates[0] if dates else '-') }..{(dates[-1] if dates else '-')}")
print(f"UNIQUE_SYMBOLS={len(symbols)}")
print(f"TRAJECTORIES={len(trajectories)}")
print()

if dates:
    print("DATES=" + " | ".join(dates[-10:]))
print()

coverage = Counter()
for symbol in symbols:
    n = len({x.as_of for x in history if x.symbol == symbol})
    coverage[n] += 1

print("=== SYMBOL DATE COVERAGE ===")
for n in sorted(coverage):
    print(f"{n}_DATES={coverage[n]}")
print()

reasons = Counter()
band_rows = []
for t in trajectories:
    if t.current_rank < 22 or t.current_rank > 80:
        reasons["OUT_OF_BAND"] += 1
        continue

    if not t.comparable:
        reasons["NONCOMPARABLE"] += 1
        continue

    missing = [
        name for name, value in (
            ("1S", t.rank_1s),
            ("3S", t.rank_3s),
            ("5S", t.rank_5s),
        )
        if value is None
    ]
    if missing:
        reasons["MISSING_" + "_".join(missing)] += 1
        band_rows.append((t, "MISSING:" + ",".join(missing)))
        continue

    monotonic = t.rank_5s > t.rank_3s > t.rank_1s > t.current_rank
    positive = t.gain_1s > 0 and t.gain_3s > 0 and t.gain_5s > 0

    if monotonic and positive:
        reasons["HEALTHY"] += 1
        status = "HEALTHY"
    elif not positive:
        reasons["NONPOSITIVE_GAIN"] += 1
        status = "NONPOSITIVE_GAIN"
    else:
        reasons["ZIGZAG"] += 1
        status = "ZIGZAG"

    band_rows.append((t, status))

print("=== REJECTION BREAKDOWN ===")
for key, value in reasons.most_common():
    print(f"{key}={value}")
print()

def show(v):
    return "—" if v is None else str(v)

def gain(v):
    if v is None:
        return "—"
    return f"{v:+d}"

print("=== BAND 22..80 — TOP DIAGNOSTIC ROWS ===")
ranked = sorted(
    band_rows,
    key=lambda row: (
        row[1] == "HEALTHY",
        row[0].gain_3s is not None,
        row[0].gain_3s if row[0].gain_3s is not None else -10**9,
        row[0].gain_5s if row[0].gain_5s is not None else -10**9,
    ),
    reverse=True,
)

for t, status in ranked[:20]:
    path = (
        f"{show(t.rank_5s)} → {show(t.rank_3s)} → "
        f"{show(t.rank_1s)} → {show(t.current_rank)}"
    )
    print(
        f"{t.symbol} | {status} | "
        f"Sıra yolu: {path} | "
        f"1S {gain(t.gain_1s)} | 3S {gain(t.gain_3s)} | 5S {gain(t.gain_5s)} | "
        f"comparable={t.comparable}"
    )

print()
if len(dates) < 6:
    print("DIAGNOSIS=RANKING_MEMORY_HAS_FEWER_THAN_6_DISTINCT_SNAPSHOTS")
    print("NEXT=BACKFILL_OR_WAIT_FOR_MORE_COMPLETED_RESEARCH_SNAPSHOTS")
elif reasons.get("HEALTHY", 0) == 0 and any(k.startswith("MISSING_") for k in reasons):
    print("DIAGNOSIS=HISTORY_EXISTS_BUT_5S_CHAIN_IS_INCOMPLETE_FOR_MANY_BAND_NAMES")
    print("NEXT=CHECK_BACKFILL_FEASIBILITY_BEFORE_RELAXING_RULE")
elif reasons.get("HEALTHY", 0) == 0:
    print("DIAGNOSIS=ENOUGH_HISTORY_BUT_NO_STRICT_MONOTONIC_PATH_IN_CURRENT_BAND")
    print("NEXT=REVIEW_ZIGZAG_VS_CONTROLLED_STRENGTHENING_POLICY")
else:
    print("DIAGNOSIS=HEALTHY_PATHS_EXIST")
    print("NEXT=CHECK_PRIMARY5_EXCLUSIONS_AND_DAILY_UI")

print("TRAJECTORY_DIAGNOSTIC=PASS")
'@

    [System.IO.File]::WriteAllText(
        $tmp,
        $code,
        (New-Object System.Text.UTF8Encoding($false))
    )

    & $Python $tmp
    if ($LASTEXITCODE -ne 0) {
        throw "TRAJECTORY_DIAGNOSTIC_FAIL"
    }
}
finally {
    if (Test-Path -LiteralPath $tmp) {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }

    if ($null -eq $oldPythonPath) {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    } else {
        $env:PYTHONPATH = $oldPythonPath
    }
}
