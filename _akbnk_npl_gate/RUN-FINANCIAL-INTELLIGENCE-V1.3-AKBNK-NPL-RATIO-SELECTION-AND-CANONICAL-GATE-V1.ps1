param(
    [string]$ProjectRoot="D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference="Stop"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Backend = Join-Path $ProjectRoot "backend"

$ScriptDst = Join-Path $Backend "scripts\run_financial_intelligence_v1_3_akbnk_npl_ratio_selection_and_canonical_gate.py"
$TestDst = Join-Path $Backend "tests\test_financial_intelligence_v1_3_akbnk_npl_ratio_selection_and_canonical_gate_v1.py"

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "run_financial_intelligence_v1_3_akbnk_npl_ratio_selection_and_canonical_gate.py") -Destination $ScriptDst -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "test_financial_intelligence_v1_3_akbnk_npl_ratio_selection_and_canonical_gate_v1.py") -Destination $TestDst -Force

$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONPATH=$Backend

Set-Location $ProjectRoot

& $Python $ScriptDst $ProjectRoot
if($LASTEXITCODE -ne 0){ throw "AKBNK_NPL_RATIO_SELECTION_AND_CANONICAL_GATE_FAILED" }

& $Python -m pytest `
  $TestDst `
  "backend\tests\test_financial_intelligence_bank_production_source_onboarding_v1.py" `
  -q

if($LASTEXITCODE -ne 0){ throw "AKBNK_NPL_RATIO_SELECTION_AND_CANONICAL_GATE_TESTS_FAILED" }

Write-Host "AKBNK_NPL_RATIO_SELECTION_AND_CANONICAL_GATE_TESTS=PASS"
Write-Host "FINANCIAL_INTELLIGENCE_V1_3_AKBNK_NPL_RATIO_SELECTION_AND_CANONICAL_GATE_V1=PASS"
