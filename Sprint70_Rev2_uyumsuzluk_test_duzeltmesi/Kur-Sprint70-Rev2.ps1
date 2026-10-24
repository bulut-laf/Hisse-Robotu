param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item `
    "$packageRoot\backend\tests\test_divergence_analysis_dashboard.py" `
    "$ProjectRoot\backend\tests\test_divergence_analysis_dashboard.py" `
    -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_divergence_analysis.py `
    backend/tests/test_divergence_analysis_dashboard.py `
    backend/tests/test_technical_decision_matrix.py `
    backend/tests/test_technical_decision_matrix_dashboard.py `
    backend/tests/test_technical_confirmation.py `
    backend/tests/test_trade_plan.py `
    backend/tests/test_live_analysis_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
