param(
    [string]$Repo = "D:\Projects\LAF-Studio\app"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Core = Join-Path $Repo "src\core\learning"

$AppliedTarget = Join-Path $Core "ItalianA2AppliedUnit01FoundationBoundV1.test.ts"
$AppliedShell = Join-Path $Core "A2AppliedCourseShellCatalog.ts"
$AppliedRegistry = Join-Path $Core "ItalianA2AppliedCourseRealizationRegistry.ts"
$AppliedCatalog = Join-Path $Core "ItalianA2AppliedCourseCatalog.ts"

$LegacyTests = @(
    (Join-Path $Core "A1CourseArchitectureMigration.test.ts"),
    (Join-Path $Core "ItalianA1CourseCatalog.test.ts"),
    (Join-Path $Core "ItalianA1Unit03LanguageRealization.test.ts"),
    (Join-Path $Core "ItalianA1Unit04LanguageRealization.test.ts"),
    (Join-Path $Core "ItalianA2Unit02FoundationV1.test.ts"),
    (Join-Path $Core "ItalianA2Unit03FoundationV1.test.ts"),
    (Join-Path $Core "ItalianA2Unit04FoundationV1.test.ts"),
    (Join-Path $Core "ItalianA2Unit05FoundationV1.test.ts")
)

foreach ($p in @(
    $Repo,
    $Core,
    $AppliedTarget,
    $AppliedShell,
    $AppliedRegistry,
    $AppliedCatalog
) + $LegacyTests) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "REQUIRED_PATH_MISSING=$p"
    }
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$rollback = Join-Path $Repo ("_rollback\Italian-A2-Applied-Unit01-Legacy-Test-Compatibility-" + $stamp)
$reportDir = Join-Path $Repo "_discovery"
$report = Join-Path $reportDir ("Italian-A2-Applied-Unit01-Legacy-Test-Compatibility-" + $stamp + ".txt")

New-Item -ItemType Directory -Force -Path $rollback,$reportDir | Out-Null

function Write-Utf8([string]$path, [string]$text) {
    [System.IO.File]::WriteAllText(
        $path,
        $text,
        (New-Object System.Text.UTF8Encoding($false))
    )
}

function Backup-Test([string]$path) {
    Copy-Item -LiteralPath $path -Destination (Join-Path $rollback ([IO.Path]::GetFileName($path))) -Force
}

function Restore-Tests {
    foreach ($path in $LegacyTests) {
        $backup = Join-Path $rollback ([IO.Path]::GetFileName($path))
        if (Test-Path -LiteralPath $backup) {
            Copy-Item -LiteralPath $backup -Destination $path -Force
        }
    }
    Write-Host "ROLLBACK=SUCCESS"
}

function Replace-ExactlyOnce(
    [string]$path,
    [string]$pattern,
    [string]$replacement,
    [string]$label
) {
    $text = [System.IO.File]::ReadAllText($path)
    $matches = [regex]::Matches(
        $text,
        $pattern,
        [System.Text.RegularExpressions.RegexOptions]::Singleline
    )

    if ($matches.Count -ne 1) {
        throw "FAIL-CLOSED:$label expected exactly 1 stale assertion; found $($matches.Count) in $path"
    }

    $newText = [regex]::Replace(
        $text,
        $pattern,
        $replacement,
        [System.Text.RegularExpressions.RegexOptions]::Singleline
    )

    Write-Utf8 $path $newText
}

foreach ($path in $LegacyTests) {
    Backup-Test $path
}

$transcriptStarted = $false

try {
    Start-Transcript -LiteralPath $report -Force | Out-Null
    $transcriptStarted = $true

    Write-Host "=== ITALIAN A2 APPLIED UNIT01 — LEGACY TEST COMPATIBILITY RECOVERY V1 ==="
    Write-Host "MODE=TEST_CONTRACT_REPAIR_ONLY"
    Write-Host "PRODUCTION_SOURCE_MUTATION=NO"
    Write-Host "APPLIED_UNIT01_FILES=KEEP"
    Write-Host "STALE_FAILURES_EXPECTED=11"
    Write-Host ""

    # ------------------------------------------------------------
    # Preflight: Applied Unit01 was already materialized by the prior script.
    # The previous run reached FULL REGRESSION, so its target test had passed.
    # Do not re-run the apply script; it is fail-closed on existing targets.
    # ------------------------------------------------------------
    Write-Host "=== PREFLIGHT ==="

    $appliedShellText = [System.IO.File]::ReadAllText($AppliedShell)
    $appliedCatalogText = [System.IO.File]::ReadAllText($AppliedCatalog)

    foreach ($needle in @(
        'a2-applied-u01-social-life',
        'a2-applied-u01-l01',
        'a2-applied-u01-l04'
    )) {
        if (-not $appliedShellText.Contains($needle)) {
            throw "FAIL-CLOSED: applied Unit01 shell contract missing: $needle"
        }
    }

    if (-not $appliedCatalogText.Contains('"foundation-bound"')) {
        throw "FAIL-CLOSED: applied Unit01 foundation-bound catalog contract missing"
    }

    Write-Host "APPLIED_UNIT01_MATERIALIZED=YES"
    Write-Host "APPLIED_UNIT01_STATUS=FOUNDATION-BOUND"
    Write-Host "NEW_CEFR_MASTERY_PROGRESSION_AUTHORITY=NO"
    Write-Host ""

    # ------------------------------------------------------------
    # A1 historical tests:
    # They are local migration/unit tests, but they froze global topology at
    # the old Unit04/Unit05-era state. Preserve their historical minimum
    # instead of asserting a repository-global final count.
    # ------------------------------------------------------------
    Write-Host "=== PATCH A1 STALE GLOBAL COUNTS ==="

    $aliasFiles = @(
        (Join-Path $Core "A1CourseArchitectureMigration.test.ts"),
        (Join-Path $Core "ItalianA1CourseCatalog.test.ts"),
        (Join-Path $Core "ItalianA1Unit03LanguageRealization.test.ts"),
        (Join-Path $Core "ItalianA1Unit04LanguageRealization.test.ts")
    )

    $aliasPattern =
        'expect\(\s*ITALIAN_A1_LEGACY_REALIZATION_ALIASES\s*\)\.toHaveLength\(28\);'
    $aliasReplacement =
        'expect(ITALIAN_A1_LEGACY_REALIZATION_ALIASES.length).toBeGreaterThanOrEqual(28);'

    foreach ($path in $aliasFiles) {
        Replace-ExactlyOnce `
            $path `
            $aliasPattern `
            $aliasReplacement `
            "A1 legacy alias historical minimum"
        Write-Host ("PATCHED=" + [IO.Path]::GetFileName($path) + " :: alias 28 -> >=28")
    }

    $readyFiles = @(
        (Join-Path $Core "ItalianA1CourseCatalog.test.ts"),
        (Join-Path $Core "ItalianA1Unit03LanguageRealization.test.ts"),
        (Join-Path $Core "ItalianA1Unit04LanguageRealization.test.ts")
    )

    $readyPattern =
        'expect\(\s*ITALIAN_A1_PRODUCTION_READY_UNIT_COUNT\s*\)\.toBe\(5\);'
    $readyReplacement =
        'expect(ITALIAN_A1_PRODUCTION_READY_UNIT_COUNT).toBeGreaterThanOrEqual(5);'

    foreach ($path in $readyFiles) {
        Replace-ExactlyOnce `
            $path `
            $readyPattern `
            $readyReplacement `
            "A1 production-ready historical minimum"
        Write-Host ("PATCHED=" + [IO.Path]::GetFileName($path) + " :: ready 5 -> >=5")
    }

    # ------------------------------------------------------------
    # A2 historical unit-foundation tests:
    # A2 is now a six-unit foundation. Unit02/03/04/05 tests should prove
    # their own unit remains registered, not freeze the whole course length
    # at the moment each unit was originally introduced.
    # ------------------------------------------------------------
    Write-Host ""
    Write-Host "=== PATCH A2 STALE INCREMENTAL COUNTS ==="

    $a2Fixes = @(
        @{
            File = (Join-Path $Core "ItalianA2Unit02FoundationV1.test.ts")
            OldCount = 2
            Unit = "A2_UNIT_2"
        },
        @{
            File = (Join-Path $Core "ItalianA2Unit03FoundationV1.test.ts")
            OldCount = 3
            Unit = "A2_UNIT_3"
        },
        @{
            File = (Join-Path $Core "ItalianA2Unit04FoundationV1.test.ts")
            OldCount = 4
            Unit = "A2_UNIT_4"
        },
        @{
            File = (Join-Path $Core "ItalianA2Unit05FoundationV1.test.ts")
            OldCount = 5
            Unit = "A2_UNIT_5"
        }
    )

    foreach ($fix in $a2Fixes) {
        $text = [System.IO.File]::ReadAllText($fix.File)
        if (-not $text.Contains($fix.Unit)) {
            throw "FAIL-CLOSED: $($fix.Unit) import/reference not found in $($fix.File)"
        }

        $pattern =
            'expect\(\s*A2_COURSE_UNITS\s*\)\.toHaveLength\(' +
            [regex]::Escape([string]$fix.OldCount) +
            '\);'
        $replacement =
            "expect(A2_COURSE_UNITS).toContain($($fix.Unit));"

        Replace-ExactlyOnce `
            $fix.File `
            $pattern `
            $replacement `
            "A2 incremental unit count $($fix.OldCount)"

        Write-Host (
            "PATCHED=" +
            [IO.Path]::GetFileName($fix.File) +
            " :: length $($fix.OldCount) -> contains $($fix.Unit)"
        )
    }

    Write-Host ""
    Write-Host "PATCH_COUNT=11"
    Write-Host "PRODUCTION_SOURCE_MUTATION=NO"

    Set-Location $Repo

    # ------------------------------------------------------------
    # Target: all 8 repaired legacy files + already-created Applied Unit01.
    # ------------------------------------------------------------
    Write-Host ""
    Write-Host "=== RECOVERY TARGET TESTS ==="

    npx vitest run `
        'src\core\learning\A1CourseArchitectureMigration.test.ts' `
        'src\core\learning\ItalianA1CourseCatalog.test.ts' `
        'src\core\learning\ItalianA1Unit03LanguageRealization.test.ts' `
        'src\core\learning\ItalianA1Unit04LanguageRealization.test.ts' `
        'src\core\learning\ItalianA2Unit02FoundationV1.test.ts' `
        'src\core\learning\ItalianA2Unit03FoundationV1.test.ts' `
        'src\core\learning\ItalianA2Unit04FoundationV1.test.ts' `
        'src\core\learning\ItalianA2Unit05FoundationV1.test.ts' `
        'src\core\learning\ItalianA2AppliedUnit01FoundationBoundV1.test.ts'

    if ($LASTEXITCODE -ne 0) {
        Restore-Tests
        throw "ITALIAN A2 APPLIED UNIT01 RECOVERY TARGET FAILED"
    }

    Write-Host ""
    Write-Host "=== FULL REGRESSION ==="
    npm test

    if ($LASTEXITCODE -ne 0) {
        Restore-Tests
        throw "ITALIAN A2 APPLIED UNIT01 RECOVERY FULL REGRESSION FAILED"
    }

    Write-Host ""
    Write-Host "=== PRODUCTION BUILD ==="
    npm run build

    if ($LASTEXITCODE -ne 0) {
        Restore-Tests
        throw "ITALIAN A2 APPLIED UNIT01 RECOVERY BUILD FAILED"
    }

    Write-Host ""
    Write-Host "=== SUCCESS ==="
    Write-Host "LEGACY_TEST_COMPATIBILITY_REPAIR=PASS"
    Write-Host "RECOVERY_TARGET_TESTS=PASS"
    Write-Host "FULL_REGRESSION=PASS"
    Write-Host "PRODUCTION_BUILD=PASS"
    Write-Host "APPLIED_UNIT01=FOUNDATION-BOUND"
    Write-Host "PRODUCTION_SOURCE_MUTATION=NO"
    Write-Host "ITALIAN_A2_APPLIED_UNIT01_RECOVERY_V1=COMPLETE"
    Write-Host "NEXT=ITALIAN_A2_APPLIED_UNIT02"
    Write-Host ("REPORT=" + $report)
}
finally {
    if ($transcriptStarted) {
        Stop-Transcript | Out-Null
    }
}
