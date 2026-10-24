param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Dashboard = Join-Path $ProjectRoot "backend\dashboard.py"
$MarketScanner = Join-Path $ProjectRoot "backend\app\analysis\market_scanner.py"
$Test = Join-Path $ProjectRoot "backend\tests\test_ranking_memory_full_research_capture_v1.py"
$Discovery = Join-Path $ProjectRoot "_discovery"

foreach ($p in @($Python, $Dashboard, $MarketScanner)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

New-Item -ItemType Directory -Force -Path $Discovery | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$rollback = Join-Path $ProjectRoot "_rollback\daily10-full-research-capture-v1-$stamp"
$report = Join-Path $Discovery "Hisse-Robotu-Daily10-Full-Research-Capture-V1-$stamp.txt"

New-Item -ItemType Directory -Force -Path $rollback | Out-Null

$dashboardBackup = Join-Path $rollback "dashboard.py"
Copy-Item -LiteralPath $Dashboard -Destination $dashboardBackup -Force

$testExisted = Test-Path -LiteralPath $Test
if ($testExisted) {
    Copy-Item -LiteralPath $Test -Destination (Join-Path $rollback "test_ranking_memory_full_research_capture_v1.py") -Force
}

function Restore-Rollback {
    Copy-Item -LiteralPath $dashboardBackup -Destination $Dashboard -Force

    if ($testExisted) {
        Copy-Item `
            -LiteralPath (Join-Path $rollback "test_ranking_memory_full_research_capture_v1.py") `
            -Destination $Test `
            -Force
    }
    elseif (Test-Path -LiteralPath $Test) {
        Remove-Item -LiteralPath $Test -Force
    }
}

function Write-Utf8([string]$path, [string]$text) {
    [System.IO.File]::WriteAllText(
        $path,
        $text,
        (New-Object System.Text.UTF8Encoding($false))
    )
}

try {
    Write-Host "=== HISSE ROBOTU — FULL RESEARCH RANKING MEMORY CAPTURE V1 ==="
    Write-Host "MODE=CONTROLLED_SOURCE_MUTATION"
    Write-Host "RANKING_MEMORY_DATA_MUTATION=NO"
    Write-Host "GOAL=CAPTURE_FULL_FILTERED_RESEARCH_NOT_DISPLAY_SLICE"
    Write-Host "NEW_ENGINE=NO"
    Write-Host "NEW_STORE=NO"

    $dashboardText = [System.IO.File]::ReadAllText($Dashboard)
    $marketText = [System.IO.File]::ReadAllText($MarketScanner)

    Write-Host ""
    Write-Host "=== PREFLIGHT ==="

    $oldLine = "    _three_all_rows = aday_tablosu_kayitlari(sonuc)"

    $oldCount = ([regex]::Matches(
        $dashboardText,
        [regex]::Escape($oldLine)
    )).Count

    if ($oldCount -ne 1) {
        throw "FAIL-CLOSED:EXPECTED_CURRENT_DASHBOARD_CAPTURE_SEAM_COUNT=1;FOUND=$oldCount"
    }

    if ($dashboardText -notmatch 'rows\s*=\s*_three_all_rows') {
        throw "FAIL-CLOSED:RANK_OBSERVATION_ROWS_BINDING_NOT_FOUND"
    }

    if ($marketText -notmatch 'filtrelenmis\.adaylar\s*\[\s*:\s*istek\.maksimum_aday\s*\]') {
        throw "FAIL-CLOSED:DISPLAY_SLICE_CONTRACT_NOT_PROVEN"
    }

    $helperPattern = 'def\s+aday_tablosu_kayitlari[\s\S]*?for\s+sira\s*,\s*aday\s+in\s+enumerate\(\s*sonuc\.adaylar\s*,'
    if ($marketText -notmatch $helperPattern) {
        throw "FAIL-CLOSED:ADAY_TABLOSU_HELPER_DISPLAY_SOURCE_NOT_PROVEN"
    }

    Write-Host "DISPLAY_SLICE_CONTRACT=PROVEN"
    Write-Host "OLD_CAPTURE_SOURCE=aday_tablosu_kayitlari(sonuc)"
    Write-Host "OLD_HELPER_SOURCE=sonuc.adaylar"
    Write-Host "TARGET_CAPTURE_SOURCE=sonuc.filtrelenmis.adaylar"
    Write-Host "RANKING_MEMORY_DATA_MUTATION=NO"

    $newBlock = @'
    _three_all_rows = tuple(
        {
            "Sıra": _rank,
            "Hisse": _candidate.sembol.removesuffix(".IS"),
            "Skor": _candidate.sinyal.skor,
        }
        for _rank, _candidate in enumerate(
            sonuc.filtrelenmis.adaylar,
            start=1,
        )
    )
'@

    $dashboardText = $dashboardText.Replace($oldLine, $newBlock.TrimEnd("`r","`n"))
    Write-Utf8 $Dashboard $dashboardText

    $testText = @'
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "backend" / "dashboard.py"
MARKET_SCANNER = ROOT / "backend" / "app" / "analysis" / "market_scanner.py"


def _unparse(node: ast.AST) -> str:
    return ast.unparse(node).replace(" ", "")


def test_ranking_memory_capture_uses_full_filtered_research_not_display_slice():
    source = DASHBOARD.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assignments = []
    observation_calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name)
                and target.id == "_three_all_rows"
                for target in node.targets
            ):
                assignments.append(node.value)

        if isinstance(node, ast.Call):
            fn = node.func
            name = (
                fn.id
                if isinstance(fn, ast.Name)
                else fn.attr
                if isinstance(fn, ast.Attribute)
                else ""
            )
            if name == "observations_from_research_rows":
                observation_calls.append(node)

    assert len(assignments) == 1
    expression = _unparse(assignments[0])

    assert "sonuc.filtrelenmis.adaylar" in expression
    assert "aday_tablosu_kayitlari(sonuc)" not in expression
    assert "sonuc.adaylar" not in expression

    assert any(
        any(
            keyword.arg == "rows"
            and isinstance(keyword.value, ast.Name)
            and keyword.value.id == "_three_all_rows"
            for keyword in call.keywords
        )
        for call in observation_calls
    )


def test_display_helper_remains_display_only_and_is_not_repurposed():
    source = MARKET_SCANNER.read_text(encoding="utf-8")

    assert "filtrelenmis.adaylar[: istek.maksimum_aday]" in source

    tree = ast.parse(source)
    helper = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "aday_tablosu_kayitlari"
    )

    helper_source = ast.unparse(helper).replace(" ", "")
    assert "enumerate(sonuc.adaylar,start=1)" in helper_source


def test_contract_keeps_capture_observation_only():
    source = DASHBOARD.read_text(encoding="utf-8")

    assert "RANKING_JUMP_V1_BLOCK1" in source
    assert "observations_from_research_rows" in source
    assert "RankObservationJsonlStore().append_snapshot" in source
'@

    Write-Utf8 $Test $testText

    Write-Host ""
    Write-Host "=== SOURCE CONTRACT CHECK ==="

    $updated = [System.IO.File]::ReadAllText($Dashboard)

    if ($updated -notmatch 'sonuc\.filtrelenmis\.adaylar') {
        Restore-Rollback
        throw "SOURCE_CONTRACT_FAIL:FULL_FILTERED_REFERENCE_MISSING"
    }

    if ($updated.Contains($oldLine)) {
        Restore-Rollback
        throw "SOURCE_CONTRACT_FAIL:OLD_PARTIAL_CAPTURE_STILL_PRESENT"
    }

    Write-Host "FULL_FILTERED_CAPTURE_BINDING=PASS"
    Write-Host "DISPLAY_UI_HELPER=UNCHANGED"
    Write-Host "RANKING_MEMORY_EXISTING_DATA=UNCHANGED"

    Set-Location $ProjectRoot

    Write-Host ""
    Write-Host "=== TARGET TESTS ==="

    $targetOutput = & $Python -m pytest -q `
        backend/tests/test_ranking_memory_full_research_capture_v1.py `
        backend/tests/test_ranking_snapshot_adapter.py `
        backend/tests/test_daily_early_trajectory_v1.py 2>&1
    $targetExit = $LASTEXITCODE
    $targetOutput | ForEach-Object { Write-Host $_ }

    if ($targetExit -ne 0) {
        Restore-Rollback

        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "RESULT=TARGET_TEST_FAIL",
                "ROLLBACK=SUCCESS",
                "PRODUCTION_STATUS=PRE_PATCH_RESTORED",
                ""
            ) + @($targetOutput | ForEach-Object { [string]$_ })
        )

        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=TARGET_TEST_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_PATCH_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "FULL_RESEARCH_CAPTURE_TARGET_TEST_FAIL"
    }

    Write-Host ""
    Write-Host "=== FULL REGRESSION ==="

    $regOutput = & $Python -m pytest -q 2>&1
    $regExit = $LASTEXITCODE
    $regOutput | ForEach-Object { Write-Host $_ }

    if ($regExit -ne 0) {
        Restore-Rollback

        [System.IO.File]::WriteAllLines(
            $report,
            @(
                "RESULT=FULL_REGRESSION_FAIL",
                "ROLLBACK=SUCCESS",
                "PRODUCTION_STATUS=PRE_PATCH_RESTORED",
                ""
            ) +
            @($targetOutput | ForEach-Object { [string]$_ }) +
            @("") +
            @($regOutput | ForEach-Object { [string]$_ })
        )

        Write-Host ""
        Write-Host "=== FAILURE ==="
        Write-Host "ERROR=FULL_REGRESSION_FAIL"
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_PATCH_RESTORED"
        Write-Host ("REPORT=" + $report)
        throw "FULL_RESEARCH_CAPTURE_FULL_REGRESSION_FAIL"
    }

    [System.IO.File]::WriteAllLines(
        $report,
        @(
            "=== HISSE ROBOTU — FULL RESEARCH RANKING MEMORY CAPTURE V1 ===",
            "RESULT=SUCCESS",
            "DISPLAY_UI_HELPER=UNCHANGED",
            "CAPTURE_SOURCE=sonuc.filtrelenmis.adaylar",
            "RANKING_MEMORY_EXISTING_DATA=UNCHANGED",
            "TARGET_TEST=PASS",
            "FULL_REGRESSION=PASS",
            "NEXT=REBUILD_25AUG_CANONICAL_RANKING_MEMORY_SESSION_THEN_RETRY_HISTORICAL_BACKFILL",
            ""
        ) +
        @($targetOutput | ForEach-Object { [string]$_ }) +
        @("") +
        @($regOutput | ForEach-Object { [string]$_ })
    )

    Write-Host ""
    Write-Host "=== SUCCESS ==="
    Write-Host "FULL_RESEARCH_CAPTURE_CONTRACT=PROVEN_AND_PATCHED"
    Write-Host "DISPLAY_UI_HELPER=UNCHANGED"
    Write-Host "RANKING_MEMORY_EXISTING_DATA=UNCHANGED"
    Write-Host "TARGET_TEST=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "DAILY10_FULL_RESEARCH_CAPTURE_V1=COMPLETE"
    Write-Host "NEXT=REBUILD_25AUG_CANONICAL_RANKING_MEMORY_SESSION_THEN_RETRY_HISTORICAL_BACKFILL"
    Write-Host ("REPORT=" + $report)
}
catch {
    if ($_.Exception.Message -notmatch "FULL_RESEARCH_CAPTURE_TARGET_TEST_FAIL|FULL_RESEARCH_CAPTURE_FULL_REGRESSION_FAIL|SOURCE_CONTRACT_FAIL") {
        Restore-Rollback
        Write-Host "ROLLBACK=SUCCESS"
        Write-Host "PRODUCTION_STATUS=PRE_PATCH_RESTORED"
    }
    throw
}
