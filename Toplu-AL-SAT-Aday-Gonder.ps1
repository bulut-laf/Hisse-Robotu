param(
    [string]$CsvPath = "",
    [string]$Symbols = "",
    [string]$AlsatUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$CacheDir = "D:\Projects\Hisse-Robotu\data\candidate_cache"
$CacheFile = Join-Path $CacheDir "ON_YUKSELIS_SON_ADAYLAR.csv"

function Test-TrueValue([object]$Value) {
    if ($null -eq $Value) { return $false }
    $text = [string]$Value
    return $text.Trim().ToLowerInvariant() -in @("true","1","evet","yes")
}

function Get-PropValue($Row, [string[]]$Names) {
    foreach ($name in $Names) {
        $prop = $Row.PSObject.Properties[$name]
        if ($null -ne $prop) { return $prop.Value }
    }
    return $null
}

if ([string]::IsNullOrWhiteSpace($CsvPath)) {
    if (-not (Test-Path -LiteralPath $CacheFile -PathType Leaf)) {
        throw "Kayitli son aday CSV bulunamadi. Ilk kullanimda -CsvPath verin."
    }
    $CsvPath = $CacheFile
}
else {
    if (-not (Test-Path -LiteralPath $CsvPath -PathType Leaf)) {
        throw "CSV bulunamadi: $CsvPath"
    }
    New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
    Copy-Item -LiteralPath $CsvPath -Destination $CacheFile -Force
}

$rows = @(Import-Csv -LiteralPath $CsvPath -Encoding UTF8)
if ($rows.Count -eq 0) {
    throw "CSV bos."
}

$requested = @()
if (-not [string]::IsNullOrWhiteSpace($Symbols)) {
    $requested = @(
        $Symbols.Split(",") |
        ForEach-Object { $_.Trim().ToUpperInvariant() } |
        Where-Object { $_ }
    )
}

$candidates = foreach ($row in $rows) {
    $symbol = [string](Get-PropValue $row @("Hisse","Symbol","Sembol"))
    $symbol = $symbol.Trim().ToUpperInvariant().Replace(".IS","")
    if (-not $symbol) { continue }

    $aday = Test-TrueValue (Get-PropValue $row @("Aday","Candidate"))
    $gecGiris = Test-TrueValue (Get-PropValue $row @("Geç giriş","Gec giris","Late entry"))

    if ($requested.Count -gt 0) {
        if ($requested -notcontains $symbol) { continue }
    }
    elseif (-not $aday -or $gecGiris) {
        continue
    }

    [pscustomobject]@{
        Symbol = $symbol
        Score = Get-PropValue $row @("Hazırlık skoru","Hazirlik skoru")
        Stage = Get-PropValue $row @("Aşama","Asama")
        StageText = Get-PropValue $row @("Aşama açıklaması","Asama aciklamasi")
        AsOf = Get-PropValue $row @("Evren tarihi","Tarih","Date")
        RR = Get-PropValue $row @("Risk/ödül","Risk/odul")
    }
}

$candidates = @($candidates)
if ($candidates.Count -eq 0) {
    throw "Gonderilecek aday bulunamadi."
}

$sent = 0
$failed = 0

foreach ($c in $candidates) {
    $payload = @{
        symbol = $c.Symbol
        source = "HISSE_ROBOTU_ON_YUKSELIS"
        as_of = [string]$c.AsOf
        robot_score = $c.Score
        robot_decision = [string]$c.StageText
        technical_outlook = [string]$c.Stage
        rank = $null
        risk_reward = $c.RR
    } | ConvertTo-Json -Compress

    try {
        $response = Invoke-RestMethod `
            -Uri ($AlsatUrl.TrimEnd("/") + "/api/external-candidate") `
            -Method Post `
            -ContentType "application/json; charset=utf-8" `
            -Body ([System.Text.Encoding]::UTF8.GetBytes($payload))

        Write-Host ("OK  {0,-8} skor={1} asama={2} RR={3}" -f $c.Symbol,$c.Score,$c.Stage,$c.RR) -ForegroundColor Green
        $sent++
    }
    catch {
        Write-Host ("HATA {0}: {1}" -f $c.Symbol,$_.Exception.Message) -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "TOPLU AL-SAT AKTARIM TAMAMLANDI" -ForegroundColor Cyan
Write-Host "Gonderilen: $sent"
Write-Host "Hata: $failed"
Write-Host "Son aday CSV cache: $CacheFile"

if ($failed -gt 0) {
    exit 2
}
