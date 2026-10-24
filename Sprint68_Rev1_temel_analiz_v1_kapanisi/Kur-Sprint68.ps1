param(
    [string]$ProjectRoot = "D:\Projects\Hisse-Robotu"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Proje sanal ortamı bulunamadı: $python"
}

Copy-Item "$packageRoot\PROJECT_NOTES.md" "$ProjectRoot\PROJECT_NOTES.md" -Force
Copy-Item "$packageRoot\KULLANIM_KILAVUZU.md" "$ProjectRoot\KULLANIM_KILAVUZU.md" -Force
Copy-Item "$packageRoot\TEMEL_ANALIZ_V1_KAPANIS.md" "$ProjectRoot\TEMEL_ANALIZ_V1_KAPANIS.md" -Force
Copy-Item "$packageRoot\TEMEL_ANALIZ_V1_MANIFEST.json" "$ProjectRoot\TEMEL_ANALIZ_V1_MANIFEST.json" -Force
Copy-Item "$packageRoot\Hazirla-Temel-Analiz-V1-Snapshot.ps1" "$ProjectRoot\Hazirla-Temel-Analiz-V1-Snapshot.ps1" -Force
Copy-Item "$packageRoot\backend\tests\test_fundamental_v1_closeout.py" "$ProjectRoot\backend\tests\test_fundamental_v1_closeout.py" -Force

Set-Location $ProjectRoot

& $python -m pytest `
    backend/tests/test_fundamental_v1_closeout.py `
    backend/tests/test_fundamental_models.py `
    backend/tests/test_fundamental_data.py `
    backend/tests/test_fundamental_store.py `
    backend/tests/test_fundamental_analysis.py `
    backend/tests/test_fundamental_quality.py `
    backend/tests/test_fundamental_score_store.py `
    backend/tests/test_fundamental_score_history.py `
    backend/tests/test_sector_reference.py `
    backend/tests/test_sector_score_ranking.py `
    backend/tests/test_sector_strength_map.py `
    backend/tests/test_fundamental_report.py `
    backend/tests/test_fundamental_report_archive.py `
    backend/tests/test_fundamental_report_archive_filter.py `
    backend/tests/test_fundamental_settings.py `
    backend/tests/test_fundamental_settings_integration.py `
    backend/tests/test_streamlit_api_compatibility.py -q
