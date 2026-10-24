param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item "$packageRoot\backend\app\analysis\signal_outcome_tracking.py" "$ProjectRoot\backend\app\analysis\signal_outcome_tracking.py" -Force
Copy-Item "$packageRoot\backend\app\analysis\indicator_contribution.py" "$ProjectRoot\backend\app\analysis\indicator_contribution.py" -Force
Copy-Item "$packageRoot\backend\dashboard.py" "$ProjectRoot\backend\dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_indicator_contribution.py" "$ProjectRoot\backend\tests\test_indicator_contribution.py" -Force
Copy-Item "$packageRoot\backend\tests\test_indicator_contribution_dashboard.py" "$ProjectRoot\backend\tests\test_indicator_contribution_dashboard.py" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_indicator_contribution.py `
    backend/tests/test_indicator_contribution_dashboard.py `
    backend/tests/test_signal_outcome_tracking.py `
    backend/tests/test_signal_outcome_tracking_dashboard.py `
    backend/tests/test_technical_decision_matrix.py `
    backend/tests/test_technical_decision_matrix_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
