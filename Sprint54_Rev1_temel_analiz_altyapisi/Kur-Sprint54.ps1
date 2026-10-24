param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Copy-Item "$packageRoot\backend\app\models\fundamental_models.py" `
    "$ProjectRoot\backend\app\models\fundamental_models.py" -Force

New-Item -ItemType Directory `
    "$ProjectRoot\backend\app\analysis" -Force | Out-Null
Copy-Item "$packageRoot\backend\app\analysis\fundamental_analysis.py" `
    "$ProjectRoot\backend\app\analysis\fundamental_analysis.py" -Force

Copy-Item "$packageRoot\backend\app\data\fundamental_data.py" `
    "$ProjectRoot\backend\app\data\fundamental_data.py" -Force

New-Item -ItemType Directory `
    "$ProjectRoot\backend\data" -Force | Out-Null
Copy-Item "$packageRoot\backend\data\fundamental_sample.csv" `
    "$ProjectRoot\backend\data\fundamental_sample.csv" -Force

Copy-Item "$packageRoot\backend\tests\test_fundamental_models.py" `
    "$ProjectRoot\backend\tests\test_fundamental_models.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_analysis.py" `
    "$ProjectRoot\backend\tests\test_fundamental_analysis.py" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_data.py" `
    "$ProjectRoot\backend\tests\test_fundamental_data.py" -Force

Set-Location $ProjectRoot
python -m pytest `
    backend/tests/test_fundamental_models.py `
    backend/tests/test_fundamental_analysis.py `
    backend/tests/test_fundamental_data.py -q
