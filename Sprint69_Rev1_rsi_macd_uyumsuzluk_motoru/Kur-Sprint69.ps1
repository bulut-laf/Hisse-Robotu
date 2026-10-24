param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item "$packageRoot\backend\app\analysis\divergence_analysis.py" "$ProjectRoot\backend\app\analysis\divergence_analysis.py" -Force
Copy-Item "$packageRoot\backend\dashboard.py" "$ProjectRoot\backend\dashboard.py" -Force
Copy-Item "$packageRoot\backend\tests\test_divergence_analysis.py" "$ProjectRoot\backend\tests\test_divergence_analysis.py" -Force
Copy-Item "$packageRoot\backend\tests\test_divergence_analysis_dashboard.py" "$ProjectRoot\backend\tests\test_divergence_analysis_dashboard.py" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_divergence_analysis.py `
    backend/tests/test_divergence_analysis_dashboard.py `
    backend/tests/test_technical_indicators.py `
    backend/tests/test_multi_timeframe_analysis.py `
    backend/tests/test_technical_confirmation.py `
    backend/tests/test_live_analysis_dashboard.py `
    backend/tests/test_streamlit_api_compatibility.py -q
