$ErrorActionPreference = "Stop"
$Root = (Get-Location).Path
$Dashboard = Join-Path $Root "backend\dashboard.py"
if (!(Test-Path $Dashboard)) { throw "Proje kökünde backend\dashboard.py bulunamadı." }

$targets = @(
  @{ Src="backend\app\funds\hedef24_store.py"; Dst="backend\app\funds\hedef24_store.py" },
  @{ Src="backend\app\funds\hedef24_analysis.py"; Dst="backend\app\funds\hedef24_analysis.py" },
  @{ Src="backend\app\ui\hedef24_terminal.py"; Dst="backend\app\ui\hedef24_terminal.py" },
  @{ Src="backend\tests\test_hedef24_store_sprint2.py"; Dst="backend\tests\test_hedef24_store_sprint2.py" },
  @{ Src="backend\tests\test_hedef24_analysis_sprint3.py"; Dst="backend\tests\test_hedef24_analysis_sprint3.py" }
)
foreach ($item in $targets) {
  $src = Join-Path $PSScriptRoot $item.Src
  $dst = Join-Path $Root $item.Dst
  if (!(Test-Path $src)) { throw "Paket dosyası bulunamadı: $src" }
  $dir = Split-Path $dst -Parent
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  if (Test-Path $dst) {
    Copy-Item $dst "$dst.bak_sprint3fix_$(Get-Date -Format yyyyMMdd_HHmmss)"
  }
  Copy-Item $src $dst -Force
}

$raw = Get-Content -LiteralPath $Dashboard -Raw -Encoding UTF8
$pattern = '(?ms)^[ \t]*elif analiz_modu == "Erste Hungary":[\s\S]*?(?=^[ \t]*elif analiz_modu == "Fon Analiz Merkezi":)'
$replacement = @'
    elif analiz_modu == "Erste Hungary":
        from backend.app.ui.hedef24_terminal import render_hedef24_terminal
        try:
            from backend.app.ui.fund_analysis_center import _render_erste_hungary_evidence_surface
            _render_erste_hungary_evidence_surface(st)
        except ImportError:
            st.info("Erste Hungary kanıt paneli bu kurulumda bulunamadı; Hedef 24 paneli bağımsız çalışıyor.")
        render_hedef24_terminal()
'@

if ($raw -match 'from backend\.app\.ui\.hedef24_terminal import render_hedef24_terminal') {
  Write-Host "Hedef 24 dashboard bağlantısı zaten mevcut."
} else {
  $regex = [regex]::new($pattern)
  $matches = $regex.Matches($raw)
  if ($matches.Count -ne 1) {
    throw "Erste Hungary bölgesi tekil olarak bulunamadı (eşleşme: $($matches.Count)). Dashboard güvenlik için değiştirilmedi."
  }
  $backup = "$Dashboard.bak_sprint3fix_$(Get-Date -Format yyyyMMdd_HHmmss)"
  Copy-Item -LiteralPath $Dashboard -Destination $backup
  $raw = $regex.Replace($raw, $replacement, 1)
  Set-Content -LiteralPath $Dashboard -Value $raw -Encoding utf8
  Write-Host "Dashboard bağlantısı eklendi. Yedek: $backup"
}

Write-Host "Kurulum dosyaları kopyalandı."
Write-Host "Önce sözdizimi ve hedef testleri çalıştırın:"
Write-Host ".\.venv\Scripts\python.exe -m py_compile backend\app\funds\hedef24_store.py backend\app\funds\hedef24_analysis.py backend\app\ui\hedef24_terminal.py backend\dashboard.py"
Write-Host ".\.venv\Scripts\python.exe -m pytest backend\tests\test_hedef24_analysis_sprint3.py backend\tests\test_hedef24_store_sprint2.py -q"
