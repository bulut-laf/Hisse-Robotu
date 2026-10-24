param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item "$packageRoot\backend\app\data\kap_fundamental_source.py" `
    "$ProjectRoot\backend\app\data\kap_fundamental_source.py" -Force
Copy-Item "$packageRoot\backend\app\data\fundamental_store.py" `
    "$ProjectRoot\backend\app\data\fundamental_store.py" -Force
Copy-Item "$packageRoot\backend\app\analysis\kap_fundamental_service.py" `
    "$ProjectRoot\backend\app\analysis\kap_fundamental_service.py" -Force

Copy-Item "$packageRoot\backend\tests\test_kap_fundamental_source.py" `
    "$ProjectRoot\backend\tests\test_kap_fundamental_source.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_store.py" `
    "$ProjectRoot\backend\tests\test_fundamental_store.py" -Force
Copy-Item "$packageRoot\backend\tests\test_kap_fundamental_service.py" `
    "$ProjectRoot\backend\tests\test_kap_fundamental_service.py" -Force

Set-Location $ProjectRoot
python -m pytest `
    backend/tests/test_kap_fundamental_source.py `
    backend/tests/test_fundamental_store.py `
    backend/tests/test_kap_fundamental_service.py `
    backend/tests/test_fundamental_models.py `
    backend/tests/test_fundamental_analysis.py `
    backend/tests/test_fundamental_data.py `
    backend/tests/test_fundamental_dashboard.py -q
