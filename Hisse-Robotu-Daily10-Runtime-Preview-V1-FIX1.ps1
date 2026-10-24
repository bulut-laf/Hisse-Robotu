param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Helper = Join-Path $ProjectRoot "backend\app\analysis\daily_early_trajectory.py"
$Memory = Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py"
$Trajectory = Join-Path $ProjectRoot "backend\app\analysis\ranking_trajectory.py"

foreach ($p in @($Python,$Helper,$Memory,$Trajectory)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

Push-Location $ProjectRoot
try {
    Write-Host "=== HISSE ROBOTU — DAILY10 RUNTIME PREVIEW V1 FIX1 ==="
    Write-Host "MODE=READ_ONLY"
    Write-Host "MUTATION=NO"
    Write-Host "TARGET=ACTUAL_RANKING_MEMORY"
    Write-Host "IMPORT_MODE=PROJECT_ROOT_PYTHON_C"

    $code = @'
from backend.app.analysis.ranking_memory import RankObservationJsonlStore
from backend.app.analysis.ranking_trajectory import build_rank_trajectories
from backend.app.analysis.daily_early_trajectory import (
    build_daily_early_trajectory_candidates,
    daily_early_trajectory_rows,
)

history = RankObservationJsonlStore().list()
trajectories = build_rank_trajectories(history)

comparable = [x for x in trajectories if x.comparable]
band = [x for x in comparable if 22 <= x.current_rank <= 80]
healthy = build_daily_early_trajectory_candidates(
    trajectories,
    primary_symbols=(),
    limit=5,
    rank_min=22,
    rank_max=80,
)

print(f"RANK_OBSERVATIONS={len(history)}")
print(f"TRAJECTORIES={len(trajectories)}")
print(f"COMPARABLE={len(comparable)}")
print(f"BAND_22_80={len(band)}")
print(f"HEALTHY_EARLY_COUNT={len(healthy)}")
print("")

if not healthy:
    print("HEALTHY_EARLY=NONE")
    print(
        "REASON=No comparable 5S->3S->1S->today monotonic trajectory "
        "inside Research rank band 22..80 yet."
    )
else:
    print("=== EARLY TRAJECTORY TOP ===")
    for row in daily_early_trajectory_rows(healthy, start_priority=6):
        print(
            f"{row['Öncelik']}. {row['Hisse']} | "
            f"Sıra yolu: {row['Sıra yolu']} | "
            f"1S: {row['1S Δ']} | 3S: {row['3S Δ']} | 5S: {row['5S Δ']} | "
            f"{row['Hareket']}"
        )

print("")
print("RUNTIME_PREVIEW=PASS")
'@

    & $Python -c $code
    if ($LASTEXITCODE -ne 0) {
        throw "RUNTIME_PREVIEW_FAIL"
    }
}
finally {
    Pop-Location
}
