param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("Ekle", "Listele", "Dogrula", "Sil")]
    [string]$Islem = "Dogrula",

    [Parameter(Mandatory = $false)]
    [string]$Symbol,

    [Parameter(Mandatory = $false)]
    [string]$MeasureType,

    [Parameter(Mandatory = $false)]
    [string]$StartDate,

    [Parameter(Mandatory = $false)]
    [string]$EndDate,

    [Parameter(Mandatory = $false)]
    [string]$SourceReference,

    [Parameter(Mandatory = $false)]
    [string]$DeleteSymbol,

    [Parameter(Mandatory = $false)]
    [string]$DeleteSourceReference
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = Join-Path $ProjectRoot "data\vbts"
$CsvPath = Join-Path $DataDir "vbts_guncel.csv"
$Header = "symbol,measure_type,start_date,end_date,source_reference"

function Fail {
    param([string]$Message)
    Write-Host ""
    Write-Error $Message
    exit 1
}

function Ensure-DataDirectory {
    if (-not (Test-Path -LiteralPath $DataDir)) {
        New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
    }
}

function Normalize-Symbol {
    param([string]$Value)

    $Normalized = $Value.Trim().ToUpperInvariant()

    if ([string]::IsNullOrWhiteSpace($Normalized)) {
        Fail "Sembol boş bırakılamaz."
    }

    if ($Normalized.EndsWith(".IS")) {
        $Normalized = $Normalized.Substring(0, $Normalized.Length - 3)
    }

    if ($Normalized -notmatch "^[A-Z0-9]{3,10}$") {
        Fail "Sembol biçimi geçersizdir."
    }

    return $Normalized
}

function Parse-IsoDate {
    param(
        [string]$Value,
        [string]$FieldName
    )

    $Parsed = [datetime]::MinValue
    $CleanValue = $Value.Trim()

    if (-not [datetime]::TryParseExact(
        $CleanValue,
        "yyyy-MM-dd",
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::None,
        [ref]$Parsed
    )) {
        Fail "$FieldName YYYY-MM-DD biçiminde olmalıdır."
    }

    return $Parsed.Date
}

function Get-Rows {
    if (-not (Test-Path -LiteralPath $CsvPath)) {
        return @()
    }

    return @(Import-Csv -LiteralPath $CsvPath)
}

function Validate-Rows {
    param([array]$Rows)

    if ($Rows.Count -eq 0) {
        Fail "VBTS CSV dosyası kayıt içermiyor. Toplu tarama kilidi açılmayacak."
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
            Fail "Eksik CSV sütunu: $Column"
        }
    }

    foreach ($Row in $Rows) {
        $Null = Normalize-Symbol $Row.symbol
        $Start = Parse-IsoDate $Row.start_date "start_date"
        $End = Parse-IsoDate $Row.end_date "end_date"

        if ($End -lt $Start) {
            Fail "end_date, start_date tarihinden önce olamaz."
        }

        if ([string]::IsNullOrWhiteSpace($Row.measure_type)) {
            Fail "measure_type boş bırakılamaz."
        }

        if ([string]::IsNullOrWhiteSpace($Row.source_reference)) {
            Fail "source_reference boş bırakılamaz."
        }
    }
}

function Refresh-ValidatedCsv {
    param([array]$Rows)

    $TempPath = Join-Path $DataDir ("vbts_guncel.{0}.tmp" -f $PID)

    try {
        $Rows |
            Select-Object symbol, measure_type, start_date, end_date, source_reference |
            Export-Csv -LiteralPath $TempPath -NoTypeInformation -Encoding utf8

        $RefreshedRows = @(Import-Csv -LiteralPath $TempPath)
        Validate-Rows $RefreshedRows
        Write-Host "TEMP: $TempPath"
        Write-Host "CSV: $CsvPath"
       Move-Item -LiteralPath $TempPath -Destination $CsvPath -Force
    }
    catch {
        if (Test-Path -LiteralPath $TempPath) {
            Remove-Item -LiteralPath $TempPath -Force
        }
        throw
    }
}

function Enable-ManualSource {
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
}

Ensure-DataDirectory

if ($Islem -eq "Ekle") {
    if ([string]::IsNullOrWhiteSpace($Symbol)) {
        $Symbol = Read-Host "Hisse sembolü"
    }
    if ([string]::IsNullOrWhiteSpace($MeasureType)) {
        $MeasureType = Read-Host "VBTS tedbir türü"
    }
    if ([string]::IsNullOrWhiteSpace($StartDate)) {
        $StartDate = Read-Host "Başlangıç tarihi (YYYY-MM-DD)"
    }
    if ([string]::IsNullOrWhiteSpace($EndDate)) {
        $EndDate = Read-Host "Bitiş tarihi (YYYY-MM-DD)"
    }
    if ([string]::IsNullOrWhiteSpace($SourceReference)) {
        $SourceReference = Read-Host "Resmî KAP bildirim referansı"
    }

    $NormalizedSymbol = Normalize-Symbol $Symbol
    $Start = Parse-IsoDate $StartDate "start_date"
    $End = Parse-IsoDate $EndDate "end_date"
    $NormalizedStartDate = $Start.ToString("yyyy-MM-dd")
    $NormalizedEndDate = $End.ToString("yyyy-MM-dd")

    if ($End -lt $Start) {
        Fail "Bitiş tarihi başlangıç tarihinden önce olamaz."
    }

    if ([string]::IsNullOrWhiteSpace($MeasureType)) {
        Fail "VBTS tedbir türü boş bırakılamaz."
    }

    if ([string]::IsNullOrWhiteSpace($SourceReference)) {
        Fail "Resmî KAP bildirim referansı boş bırakılamaz."
    }

    $Rows = Get-Rows

    $Duplicate = @(
        $Rows | Where-Object {
            $_.symbol -eq $NormalizedSymbol -and
            $_.measure_type -eq $MeasureType.Trim() -and
            $_.start_date -eq $NormalizedStartDate -and
            $_.end_date -eq $NormalizedEndDate -and
            $_.source_reference -eq $SourceReference.Trim()
        }
    )

    if ($Duplicate.Count -gt 0) {
        Fail "Aynı VBTS kaydı zaten mevcut."
    }

    $NewRow = [pscustomobject]@{
        symbol = $NormalizedSymbol
        measure_type = $MeasureType.Trim()
        start_date = $NormalizedStartDate
        end_date = $NormalizedEndDate
        source_reference = $SourceReference.Trim()
    }

    $AllRows = @($Rows) + @($NewRow)
    $AllRows | Export-Csv -LiteralPath $CsvPath -NoTypeInformation -Encoding utf8

    Validate-Rows $AllRows
    Enable-ManualSource

    Write-Host ""
    Write-Host "VBTS kaydı eklendi ve manuel kaynak etkinleştirildi."
    Write-Host "CSV: $CsvPath"
    Write-Host "Kayıt sayısı: $($AllRows.Count)"
    exit 0
}

if ($Islem -eq "Listele") {
    $Rows = Get-Rows

    if ($Rows.Count -eq 0) {
        Write-Host "Kayıt bulunamadı."
        exit 0
    }

    $Rows | Format-Table -AutoSize
    exit 0
}

if ($Islem -eq "Sil") {
    if ([string]::IsNullOrWhiteSpace($DeleteSymbol)) {
        $DeleteSymbol = Read-Host "Silinecek hisse sembolü"
    }

    if ([string]::IsNullOrWhiteSpace($DeleteSourceReference)) {
        $DeleteSourceReference = Read-Host "Silinecek kaynak referansı"
    }

    $NormalizedDeleteSymbol = Normalize-Symbol $DeleteSymbol
    $CleanDeleteReference = $DeleteSourceReference.Trim()
    $Rows = Get-Rows

    $MatchedRows = @(
        $Rows | Where-Object {
            $_.symbol -eq $NormalizedDeleteSymbol -and
            $_.source_reference -eq $CleanDeleteReference
        }
    )

    if ($MatchedRows.Count -eq 0) {
        Fail "Silinecek kayıt bulunamadı."
    }

    $RemainingRows = @(
        $Rows | Where-Object {
            -not (
                $_.symbol -eq $NormalizedDeleteSymbol -and
                $_.source_reference -eq $CleanDeleteReference
            )
        }
    )

    if ($RemainingRows.Count -eq 0) {
        Remove-Item -LiteralPath $CsvPath -Force
    }
    else {
        $RemainingRows | Export-Csv -LiteralPath $CsvPath -NoTypeInformation -Encoding utf8
    }

    Write-Host ""
    Write-Host "VBTS kaydı silindi."
    Write-Host "Kalan kayıt sayısı: $($RemainingRows.Count)"
    exit 0
}

if ($Islem -eq "Dogrula") {
    $Rows = Get-Rows
    Validate-Rows $Rows
    Refresh-ValidatedCsv $Rows
    Enable-ManualSource

    Write-Host ""
    Write-Host "VBTS dosyası doğrulandı, güvenli biçimde yenilendi ve manuel kaynak etkinleştirildi."
    Write-Host "CSV: $CsvPath"
    Write-Host "Kayıt sayısı: $($Rows.Count)"
}
