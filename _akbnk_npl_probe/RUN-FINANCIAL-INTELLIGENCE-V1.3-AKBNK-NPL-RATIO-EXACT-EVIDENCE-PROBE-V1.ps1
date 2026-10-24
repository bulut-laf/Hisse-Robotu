param(
    [string]$ProjectRoot="D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference="Stop"

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Backend = Join-Path $ProjectRoot "backend"
$ScriptDst = Join-Path $Backend "scripts\run_financial_intelligence_v1_3_akbnk_npl_ratio_exact_evidence_probe.py"
$TestDst = Join-Path $Backend "tests\test_financial_intelligence_v1_3_akbnk_npl_ratio_exact_evidence_probe_v1.py"

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "run_financial_intelligence_v1_3_akbnk_npl_ratio_exact_evidence_probe.py") -Destination $ScriptDst -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "test_financial_intelligence_v1_3_akbnk_npl_ratio_exact_evidence_probe_v1.py") -Destination $TestDst -Force

$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONPATH=$Backend

Set-Location $ProjectRoot

& $Python $ScriptDst $ProjectRoot
if($LASTEXITCODE -ne 0){
    throw "AKBNK_NPL_RATIO_EXACT_EVIDENCE_PROBE_FAILED"
}

& $Python -m pytest $TestDst -q
if($LASTEXITCODE -ne 0){
    throw "AKBNK_NPL_RATIO_EXACT_EVIDENCE_PROBE_TEST_FAILED"
}

Write-Host "AKBNK_NPL_RATIO_EXACT_EVIDENCE_PROBE_TEST=PASS"
