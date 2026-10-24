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
    "$packageRoot\backend\tests\test_technical_analysis_v12_closeout.py" `
    "$ProjectRoot\backend\tests\test_technical_analysis_v12_closeout.py" `
    -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_divergence_analysis.py `
    backend/tests/test_divergence_analysis_dashboard.py `
    backend/tests/test_technical_decision_matrix.py `
    backend/tests/test_technical_decision_matrix_dashboard.py `
    backend/tests/test_signal_outcome_tracking.py `
    backend/tests/test_signal_outcome_tracking_dashboard.py `
    backend/tests/test_indicator_contribution.py `
    backend/tests/test_indicator_contribution_dashboard.py `
    backend/tests/test_walk_forward_calibration.py `
    backend/tests/test_walk_forward_calibration_dashboard.py `
    backend/tests/test_technical_analysis_v12_closeout.py `
    backend/tests/test_streamlit_api_compatibility.py -q
