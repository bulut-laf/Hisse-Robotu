$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Location).Path
$TestPath = Join-Path $ProjectRoot "backend\tests\test_hedef24_store_sprint2.py"
$StorePath = Join-Path $ProjectRoot "backend\app\funds\hedef24_store.py"

if (!(Test-Path $TestPath)) { throw "Test dosyasi bulunamadi: $TestPath" }
if (!(Test-Path $StorePath)) { throw "Store modulu bulunamadi: $StorePath" }

$content = Get-Content -LiteralPath $TestPath -Raw
$old = "from hedef24.store import Hedef24Store, PortfolioValidationError"
$new = "from backend.app.funds.hedef24_store import Hedef24Store, PortfolioValidationError"

if ($content.Contains($old)) {
    $backup = "$TestPath.bak_importfix_$(Get-Date -Format yyyyMMdd_HHmmss)"
    Copy-Item -LiteralPath $TestPath -Destination $backup
    $content = $content.Replace($old, $new)
    Set-Content -LiteralPath $TestPath -Value $content -Encoding utf8
    Write-Host "IMPORT DÜZELTİLDİ. Yedek: $backup"
} elseif ($content.Contains($new)) {
    Write-Host "Import zaten düzeltilmiş; değişiklik yapılmadı."
} else {
    throw "Beklenen import satiri bulunamadi. Dosya guvenlik icin degistirilmedi."
}
Write-Host "Sonraki komutlar:"
Write-Host ".\.venv\Scripts\python.exe -m py_compile backend\app\funds\hedef24_store.py"
Write-Host ".\.venv\Scripts\python.exe -m pytest backend\tests\test_hedef24_store_sprint2.py -q"
