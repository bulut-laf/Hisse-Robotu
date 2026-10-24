$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$CsvPath = Join-Path $ProjectRoot "data\vbts\vbts_guncel.csv"

Write-Host ""
Write-Host "Hisse Robotu - Manuel VBTS Kaynak Ayari"
Write-Host "----------------------------------------"
Write-Host "Beklenen dosya: $CsvPath"
Write-Host ""

if (-not (Test-Path -LiteralPath $CsvPath)) {
    Write-Error "vbts_guncel.csv bulunamadi. Once resmî KAP bildirimlerinden güncel dosyayi hazirlayin."
}

$Rows = @(Import-Csv -LiteralPath $CsvPath)

if ($Rows.Count -eq 0) {
    Write-Error "VBTS CSV dosyasi kayıt içermiyor. Toplu tarama kilidi açılmayacak."
}

$RequiredColumns = @(
    "symbol",
    "measure_type",
    "start_date",
    "end_date",
    "source_reference"
)

$ActualColumns = @($Rows[0].PSObject.Properties.Name)

foreach ($Column in $RequiredColumns) {
    if ($ActualColumns -notcontains $Column) {
        Write-Error "Eksik CSV sütunu: $Column"
    }
}

[Environment]::SetEnvironmentVariable(
    "HISSE_ROBOTU_VBTS_SOURCE",
    "manual_csv",
    "User"
)

[Environment]::SetEnvironmentVariable(
    "HISSE_ROBOTU_VBTS_CSV_PATH",
    $CsvPath,
    "User"
)

[Environment]::SetEnvironmentVariable(
    "HISSE_ROBOTU_VBTS_CSV_MAX_AGE_HOURS",
    "24",
    "User"
)

$env:HISSE_ROBOTU_VBTS_SOURCE = "manual_csv"
$env:HISSE_ROBOTU_VBTS_CSV_PATH = $CsvPath
$env:HISSE_ROBOTU_VBTS_CSV_MAX_AGE_HOURS = "24"

Write-Host ""
Write-Host "Manuel VBTS kaynagi etkinlestirildi."
Write-Host "Kaynak: manual_csv"
Write-Host "CSV: $CsvPath"
Write-Host "Azami dosya yasi: 24 saat"
Write-Host ""
Write-Host "Uygulamayi kapatip yeniden acin."
