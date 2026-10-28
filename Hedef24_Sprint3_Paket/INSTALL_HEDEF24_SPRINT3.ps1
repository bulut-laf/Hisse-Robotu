$ErrorActionPreference = "Stop"
$Root = (Get-Location).Path
$Dashboard = Join-Path $Root "backend\dashboard.py"
if (!(Test-Path $Dashboard)) { throw "Proje kökünde backend\dashboard.py bulunamadı." }

$targets = @(
  @{ Src="backend\app\funds\hedef24_analysis.py"; Dst="backend\app\funds\hedef24_analysis.py" },
  @{ Src="backend\app\ui\hedef24_terminal.py"; Dst="backend\app\ui\hedef24_terminal.py" },
  @{ Src="backend\tests\test_hedef24_analysis_sprint3.py"; Dst="backend\tests\test_hedef24_analysis_sprint3.py" }
)
foreach ($item in $targets) {
  $src = Join-Path $PSScriptRoot $item.Src
  $dst = Join-Path $Root $item.Dst
  if (!(Test-Path $src)) { throw "Paket dosyası bulunamadı: $src" }
  $dir = Split-Path $dst -Parent
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  if (Test-Path $dst) {
    Copy-Item $dst "$dst.bak_sprint3_$(Get-Date -Format yyyyMMdd_HHmmss)"
  }
  Copy-Item $src $dst -Force
}

$raw = Get-Content -LiteralPath $Dashboard -Raw -Encoding UTF8
$old = @'
        from backend.app.ui.fund_analysis_center import _render_erste_hungary_evidence_surface, render_hedef24_portfolio_manager
        import pandas as pd

        # 1. Mevcut Erste Hungary tablosu
        _render_erste_hungary_evidence_surface(st)

        # 2. Yeni eklediğimiz Hedef 24 Paneli
        # (Şimdilik portföyü veritabanından çekene kadar boş bir taslak DataFrame veriyoruz)
        df_hedef24 = pd.DataFrame(columns=["isin", "fon_adi", "guncel_fiyat", "momentum_skoru"])
        render_hedef24_portfolio_manager(df_hedef24)
'@
$new = @'
        # Hedef 24 ayrı modülde çalışır; mevcut Fon Analiz Merkezi dosyası değiştirilmez.
        from backend.app.ui.hedef24_terminal import render_hedef24_terminal
        try:
            from backend.app.ui.fund_analysis_center import _render_erste_hungary_evidence_surface
            _render_erste_hungary_evidence_surface(st)
        except ImportError:
            st.info("Erste Hungary kanıt paneli bu kurulumda bulunamadı; Hedef 24 paneli bağımsız çalışıyor.")
        render_hedef24_terminal()
'@
if ($raw.Contains($old)) {
  $backup = "$Dashboard.bak_sprint3_$(Get-Date -Format yyyyMMdd_HHmmss)"
  Copy-Item $Dashboard $backup
  $raw = $raw.Replace($old, $new)
  Set-Content -LiteralPath $Dashboard -Value $raw -Encoding utf8
  Write-Host "Dashboard Hedef 24 paneline bağlandı. Yedek: $backup"
} elseif ($raw.Contains("from backend.app.ui.hedef24_terminal import render_hedef24_terminal")) {
  Write-Host "Dashboard bağlantısı zaten mevcut."
} else {
  throw "Beklenen Erste Hungary/Hedef 24 bloğu bulunamadı. Dashboard güvenlik için değiştirilmedi."
}
Write-Host "Kurulum kopyalandı. Hedef testleri ve py_compile çalıştırın."
Write-Host ".\.venv\Scripts\python.exe -m py_compile backend\app\funds\hedef24_analysis.py backend\app\ui\hedef24_terminal.py backend\dashboard.py"
Write-Host ".\.venv\Scripts\python.exe -m pytest backend\tests\test_hedef24_analysis_sprint3.py backend\tests\test_hedef24_store_sprint2.py -q"
