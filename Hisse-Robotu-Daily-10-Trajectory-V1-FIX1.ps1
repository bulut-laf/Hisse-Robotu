param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Dashboard = Join-Path $ProjectRoot "backend\dashboard.py"
$Trajectory = Join-Path $ProjectRoot "backend\app\analysis\ranking_trajectory.py"
$Memory = Join-Path $ProjectRoot "backend\app\analysis\ranking_memory.py"
$Helper = Join-Path $ProjectRoot "backend\app\analysis\daily_early_trajectory.py"
$Test = Join-Path $ProjectRoot "backend\tests\test_daily_early_trajectory_v1.py"

foreach ($p in @($Python,$Dashboard,$Trajectory,$Memory)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$Backup = Join-Path $ProjectRoot ("_rollback\Daily10-Trajectory-V1-" + $stamp)
$ReportDir = Join-Path $ProjectRoot "_discovery"
$Report = Join-Path $ReportDir ("Hisse-Robotu-Daily10-Trajectory-V1-" + $stamp + ".txt")
New-Item -ItemType Directory -Force -Path $Backup,$ReportDir | Out-Null

$mutation = $false
$transcript = $false
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Save-Original([string]$Source,[string]$Name) {
    if (Test-Path -LiteralPath $Source) {
        Copy-Item -LiteralPath $Source -Destination (Join-Path $Backup $Name) -Force
    }
}

function Rollback {
    $savedDashboard = Join-Path $Backup "dashboard.py"
    if (Test-Path $savedDashboard) {
        Copy-Item $savedDashboard $Dashboard -Force
    }

    $savedHelper = Join-Path $Backup "daily_early_trajectory.py"
    if (Test-Path $savedHelper) {
        Copy-Item $savedHelper $Helper -Force
    }
    elseif (Test-Path $Helper) {
        Remove-Item $Helper -Force
    }

    $savedTest = Join-Path $Backup "test_daily_early_trajectory_v1.py"
    if (Test-Path $savedTest) {
        Copy-Item $savedTest $Test -Force
    }
    elseif (Test-Path $Test) {
        Remove-Item $Test -Force
    }

    Write-Host "ROLLBACK=SUCCESS"
}

try {
    Start-Transcript -LiteralPath $Report -Force | Out-Null
    $transcript = $true

    Write-Host "=== HISSE ROBOTU — DAILY 10 + TRAJECTORY V1 FIX1 ==="
    Write-Host "PRIMARY_OPERATION_CANDIDATES=5"
    Write-Host "EARLY_RESEARCH_CANDIDATES=UP_TO_5"
    Write-Host "EARLY_RESEARCH_BAND=22..80"
    Write-Host "PATH=5S->3S->1S->TODAY"
    Write-Host "SORT=HEALTHY_PATH_THEN_3S_THEN_5S_THEN_1S_THEN_CURRENT_RANK"
    Write-Host "NEW_COMPOSITE_SCORE=NO"
    Write-Host "AL_SAT_AUTHORITY=UNCHANGED"
    Write-Host "PRIMARY_DECISION_LIMIT=5"
    Write-Host "LEGACY_5_HEADING_CONTRACT=PRESERVED"

    $dashboardText = [System.IO.File]::ReadAllText($Dashboard)

    if ($dashboardText.Contains("DAILY_10_TRAJECTORY_V1")) {
        throw "NO_MUTATION_STOP:DAILY_10_TRAJECTORY_V1_ALREADY_PRESENT"
    }

    $requiredDashboardContracts = @(
        'st.markdown("#### Bugünün 5 Adayı")',
        'build_morning_operation_snapshot(',
        'limit=5,',
        '# V1_OPERATIONS_01D_DECISION_CARDS',
        'build_daily_buy_decisions(',
        'High-Conviction Buy Gate',
        'yeni teknik skor, işlem sinyali veya AL/SAT kararı üretmez'
    )
    foreach ($needle in $requiredDashboardContracts) {
        if (-not $dashboardText.Contains($needle)) {
            throw "NO_MUTATION_STOP:DASHBOARD_CONTRACT_MISSING=$needle"
        }
    }

    $trajectoryText = [System.IO.File]::ReadAllText($Trajectory)
    $requiredTrajectoryContracts = @(
        'class RankTrajectory',
        'current_rank',
        'rank_1s',
        'rank_3s',
        'rank_5s',
        'gain_1s',
        'gain_3s',
        'gain_5s',
        'comparable',
        'build_rank_trajectories'
    )
    foreach ($needle in $requiredTrajectoryContracts) {
        if (-not $trajectoryText.Contains($needle)) {
            throw "NO_MUTATION_STOP:TRAJECTORY_CONTRACT_MISSING=$needle"
        }
    }

    Save-Original $Dashboard "dashboard.py"
    Save-Original $Helper "daily_early_trajectory.py"
    Save-Original $Test "test_daily_early_trajectory_v1.py"

    $helperText = @'
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.app.analysis.ranking_trajectory import RankTrajectory


DEFAULT_EARLY_RANK_MIN = 22
DEFAULT_EARLY_RANK_MAX = 80
DEFAULT_EARLY_LIMIT = 5


@dataclass(frozen=True)
class DailyEarlyTrajectoryCandidate:
    symbol: str
    current_rank: int
    rank_1s: int
    rank_3s: int
    rank_5s: int
    gain_1s: int
    gain_3s: int
    gain_5s: int
    movement: str = "SAĞLIKLI İVMELENME"

    @property
    def rank_path(self) -> str:
        return (
            f"{self.rank_5s} → {self.rank_3s} → "
            f"{self.rank_1s} → {self.current_rank}"
        )


def _healthy_rank_path(item: RankTrajectory) -> bool:
    values = (
        item.rank_5s,
        item.rank_3s,
        item.rank_1s,
        item.current_rank,
        item.gain_1s,
        item.gain_3s,
        item.gain_5s,
    )
    if any(value is None for value in values):
        return False

    return bool(
        item.rank_5s > item.rank_3s > item.rank_1s > item.current_rank
        and item.gain_1s > 0
        and item.gain_3s > 0
        and item.gain_5s > 0
    )


def build_daily_early_trajectory_candidates(
    trajectories: Iterable[RankTrajectory],
    *,
    primary_symbols: Iterable[str] = (),
    limit: int = DEFAULT_EARLY_LIMIT,
    rank_min: int = DEFAULT_EARLY_RANK_MIN,
    rank_max: int = DEFAULT_EARLY_RANK_MAX,
) -> tuple[DailyEarlyTrajectoryCandidate, ...]:
    """
    Read-only early-research selection.

    This is not a score and has no AL/SAT authority. It selects only
    comparable Research trajectories whose 5S -> 3S -> 1S -> today path
    improves monotonically inside the configured research rank band.

    Ordering is deterministic:
    1) 3S rank gain descending (primary early-visibility horizon)
    2) 5S rank gain descending (persistence context)
    3) 1S rank gain descending (latest continuation)
    4) current Research rank ascending
    5) symbol ascending
    """
    if limit < 1:
        raise ValueError("limit 1 veya daha büyük olmalıdır")
    if rank_min < 1 or rank_max < rank_min:
        raise ValueError("rank bandı geçersiz")

    excluded = {
        str(symbol).removesuffix(".IS").upper().strip()
        for symbol in primary_symbols
    }

    candidates: list[DailyEarlyTrajectoryCandidate] = []
    for item in trajectories:
        symbol = str(item.symbol).removesuffix(".IS").upper().strip()
        if symbol in excluded:
            continue
        if not item.comparable:
            continue
        if item.current_rank < rank_min or item.current_rank > rank_max:
            continue
        if not _healthy_rank_path(item):
            continue

        candidates.append(
            DailyEarlyTrajectoryCandidate(
                symbol=symbol,
                current_rank=int(item.current_rank),
                rank_1s=int(item.rank_1s),
                rank_3s=int(item.rank_3s),
                rank_5s=int(item.rank_5s),
                gain_1s=int(item.gain_1s),
                gain_3s=int(item.gain_3s),
                gain_5s=int(item.gain_5s),
            )
        )

    candidates.sort(
        key=lambda item: (
            -item.gain_3s,
            -item.gain_5s,
            -item.gain_1s,
            item.current_rank,
            item.symbol,
        )
    )
    return tuple(candidates[:limit])


def daily_early_trajectory_rows(
    candidates: Iterable[DailyEarlyTrajectoryCandidate],
    *,
    start_priority: int = 6,
) -> tuple[dict[str, object], ...]:
    if start_priority < 1:
        raise ValueError("start_priority 1 veya daha büyük olmalıdır")

    rows = []
    for offset, item in enumerate(candidates):
        rows.append(
            {
                "Öncelik": start_priority + offset,
                "Hisse": item.symbol,
                "Sıra yolu": item.rank_path,
                "1S Δ": f"+{item.gain_1s}",
                "3S Δ": f"+{item.gain_3s}",
                "5S Δ": f"+{item.gain_5s}",
                "Bugün": f"#{item.current_rank}",
                "Hareket": item.movement,
            }
        )
    return tuple(rows)
'@

    $testText = @'
from pathlib import Path

from backend.app.analysis.daily_early_trajectory import (
    build_daily_early_trajectory_candidates,
    daily_early_trajectory_rows,
)
from backend.app.analysis.ranking_trajectory import RankTrajectory


def traj(
    symbol: str,
    *,
    current: int,
    r1: int,
    r3: int,
    r5: int,
    comparable: bool = True,
) -> RankTrajectory:
    return RankTrajectory(
        symbol=symbol,
        as_of="2026-08-25",
        current_rank=current,
        current_universe_size=548,
        rank_1s=r1,
        rank_3s=r3,
        rank_5s=r5,
        week_start_rank=r5,
        gain_1s=r1 - current,
        gain_3s=r3 - current,
        gain_5s=r5 - current,
        normalized_current=current / 548,
        normalized_3s=r3 / 548,
        normalized_gain_3s=(r3 - current) / 548,
        lifecycle="IVMELENIYOR",
        zone_events=(),
        comparable=comparable,
    )


def test_healthy_path_is_selected_and_sorted_by_3s_then_5s_then_1s():
    rows = (
        traj("AAA", current=26, r1=41, r3=68, r5=96),  # +15 / +42 / +70
        traj("BBB", current=29, r1=39, r3=59, r5=90),  # +10 / +30 / +61
        traj("CCC", current=24, r1=31, r3=54, r5=80),  # +7 / +30 / +56
    )
    result = build_daily_early_trajectory_candidates(rows)
    assert [item.symbol for item in result] == ["AAA", "BBB", "CCC"]
    assert result[0].rank_path == "96 → 68 → 41 → 26"
    assert (result[0].gain_1s, result[0].gain_3s, result[0].gain_5s) == (
        15,
        42,
        70,
    )


def test_zigzag_primary_duplicate_out_of_band_and_noncomparable_are_excluded():
    rows = (
        traj("GOOD", current=30, r1=45, r3=70, r5=100),
        traj("ZIG", current=26, r1=55, r3=41, r5=96),
        traj("PRIMARY", current=27, r1=40, r3=60, r5=90),
        traj("TOP", current=15, r1=30, r3=50, r5=75),
        traj("BLOCK", current=28, r1=45, r3=65, r5=95, comparable=False),
    )
    result = build_daily_early_trajectory_candidates(
        rows,
        primary_symbols=("PRIMARY",),
    )
    assert [item.symbol for item in result] == ["GOOD"]


def test_rows_show_exact_rank_path_and_gains():
    item = build_daily_early_trajectory_candidates(
        (traj("AAA", current=26, r1=41, r3=68, r5=96),)
    )[0]
    row = daily_early_trajectory_rows((item,))[0]
    assert row["Öncelik"] == 6
    assert row["Sıra yolu"] == "96 → 68 → 41 → 26"
    assert row["1S Δ"] == "+15"
    assert row["3S Δ"] == "+42"
    assert row["5S Δ"] == "+70"
    assert row["Hareket"] == "SAĞLIKLI İVMELENME"


def test_dashboard_keeps_primary_five_decision_authority_and_adds_early_five():
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "DAILY_10_TRAJECTORY_V1" in source
    assert 'st.markdown("#### Bugünün 10 Araştırma Adayı")' in source
    assert 'st.markdown("#### Bugünün 5 Adayı")' in source
    assert "limit=5," in source
    assert "build_daily_buy_decisions(" in source
    assert "Erken 5 — sağlıklı sıra göçü" in source
    assert "daily_early_trajectory_rows" in source
    assert "yeni teknik skor, işlem sinyali veya AL/SAT kararı üretmez" in source
'@

    [System.IO.File]::WriteAllText($Helper,$helperText,$utf8)
    [System.IO.File]::WriteAllText($Test,$testText,$utf8)

    $oldHeading = '    st.markdown("#### Bugünün 5 Adayı")'
    $newHeading = @'
    # DAILY_10_TRAJECTORY_V1
    st.markdown("#### Bugünün 10 Araştırma Adayı")
    st.caption(
        "İlk 5 mevcut operasyon/karar adayını aynen korur. Ek 5 araştırma adayı, "
        "22–80 Research bandında 5S → 3S → 1S → bugün sırası sürekli iyileşen "
        "sağlıklı sıra göçlerinden seçilir. Erken 5 yeni teknik skor, işlem sinyali "
        "veya AL/SAT kararı üretmez."
    )
    # Legacy V1 Operations wiring contract intentionally preserved.
    st.markdown("#### Bugünün 5 Adayı")
'@
    if (([regex]::Matches($dashboardText,[regex]::Escape($oldHeading))).Count -ne 1) {
        throw "NO_MUTATION_STOP:HEADING_ANCHOR_COUNT_INVALID"
    }
    $dashboardText = $dashboardText.Replace($oldHeading,$newHeading)

    $oldReady = @'
            st.success(
                f"{_morning_snapshot.candidate_count} aday operasyona hazır."
            )
            st.dataframe(
'@
    $newReady = @'
            st.success(
                f"{_morning_snapshot.candidate_count} ana operasyon adayı hazır."
            )
            st.markdown("##### Ana 5 — mevcut operasyon adayları")
            st.dataframe(
'@
    if (([regex]::Matches($dashboardText,[regex]::Escape($oldReady))).Count -ne 1) {
        throw "NO_MUTATION_STOP:PRIMARY_READY_ANCHOR_COUNT_INVALID"
    }
    $dashboardText = $dashboardText.Replace($oldReady,$newReady)

    $decisionAnchor = '            # V1_OPERATIONS_01D_DECISION_CARDS'
    if (([regex]::Matches($dashboardText,[regex]::Escape($decisionAnchor))).Count -ne 1) {
        throw "NO_MUTATION_STOP:DECISION_ANCHOR_COUNT_INVALID"
    }

    $earlyBlock = @'
            # DAILY_10_TRAJECTORY_V1_EARLY_FIVE
            st.markdown("##### Erken 5 — sağlıklı sıra göçü")
            st.caption(
                "Sıralama: önce 3S sıra kazancı, sonra 5S kalıcılık, sonra 1S devam "
                "ve son olarak bugünkü Research sırası. Composite skor yoktur."
            )
            try:
                from backend.app.analysis.daily_early_trajectory import (
                    build_daily_early_trajectory_candidates,
                    daily_early_trajectory_rows,
                )
                from backend.app.analysis.ranking_memory import (
                    RankObservationJsonlStore,
                )
                from backend.app.analysis.ranking_trajectory import (
                    build_rank_trajectories,
                )

                _daily10_rank_history = RankObservationJsonlStore().list()
                _daily10_trajectories = build_rank_trajectories(
                    _daily10_rank_history
                )
                _daily10_primary_symbols = tuple(
                    item.symbol for item in _morning_snapshot.candidates
                )
                _daily10_early_candidates = (
                    build_daily_early_trajectory_candidates(
                        _daily10_trajectories,
                        primary_symbols=_daily10_primary_symbols,
                        limit=5,
                        rank_min=22,
                        rank_max=80,
                    )
                )
                if _daily10_early_candidates:
                    st.dataframe(
                        pd.DataFrame(
                            daily_early_trajectory_rows(
                                _daily10_early_candidates,
                                start_priority=6,
                            )
                        ),
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info(
                        "Bugün 5S → 3S → 1S → bugün boyunca sürekli iyileşen, "
                        "22–80 bandında ve karşılaştırılabilir ek erken aday yok. "
                        "Liste düşük kaliteli adayla zorla 10'a tamamlanmadı."
                    )
            except (OSError, ValueError, TypeError) as _daily10_trajectory_error:
                st.warning(
                    "Erken 5 sıra yolu hazırlanamadı; Ana 5 ve mevcut AL/SAT "
                    "karar zinciri değişmeden çalışmaya devam ediyor. "
                    f"Detay: {_daily10_trajectory_error}"
                )
            # DAILY_10_TRAJECTORY_V1_EARLY_FIVE_END

'@

    $dashboardText = $dashboardText.Replace(
        $decisionAnchor,
        $earlyBlock + $decisionAnchor
    )

    [System.IO.File]::WriteAllText($Dashboard,$dashboardText,$utf8)
    $mutation = $true

    Write-Host "MUTATION=APPLIED"
    Write-Host "PRIMARY5=UNCHANGED"
    Write-Host "EARLY5=READ_ONLY_TRAJECTORY"
    Write-Host "FORCED_FILL_TO_10=NO"
    Write-Host "AL_SAT_AUTHORITY=UNCHANGED"

    Write-Host ""
    Write-Host "=== PY COMPILE ==="
    & $Python -m py_compile $Helper $Test $Dashboard
    if ($LASTEXITCODE -ne 0) { throw "PY_COMPILE_FAIL" }

    Write-Host ""
    Write-Host "=== TARGET TEST ==="
    Push-Location $ProjectRoot
    try {
        & $Python -m pytest $Test -q
        if ($LASTEXITCODE -ne 0) { throw "TARGET_TEST_FAIL" }
    }
    finally { Pop-Location }

    Write-Host ""
    Write-Host "=== FULL REGRESSION ==="
    Push-Location $ProjectRoot
    try {
        & $Python -m pytest backend/tests -q
        if ($LASTEXITCODE -ne 0) { throw "FULL_REGRESSION_FAIL" }
    }
    finally { Pop-Location }

    Write-Host ""
    Write-Host "=== SUCCESS ==="
    Write-Host "TARGET_TEST=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "DAILY10_TRAJECTORY_V1_FIX1=COMPLETE"
    Write-Host "EXPECTED_UI=ANA5_PLUS_UP_TO5_HEALTHY_EARLY"
    Write-Host "EXAMPLE_PATH=96 -> 68 -> 41 -> 26"
    Write-Host "EXAMPLE_GAINS=1S:+15 3S:+42 5S:+70"
    Write-Host ("REPORT=" + $Report)
}
catch {
    Write-Host ""
    Write-Host "=== FAILURE ==="
    Write-Host ("ERROR=" + $_.Exception.Message)
    if ($mutation) { Rollback }
    else { Write-Host "ROLLBACK=NOT_NEEDED_NO_MUTATION" }
    Write-Host "PRODUCTION_STATUS=UNCHANGED"
    Write-Host "NEXT=EXACT_RCA_ONLY"
    Write-Host ("REPORT=" + $Report)
    throw
}
finally {
    if ($transcript) {
        try { Stop-Transcript | Out-Null } catch {}
    }
}
