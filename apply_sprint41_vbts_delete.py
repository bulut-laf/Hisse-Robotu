from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "VBTS-Hizli-Hazirla.ps1"
BACKUP = TARGET.with_suffix(".ps1.sprint41-delete.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8-sig")
    shutil.copy2(TARGET, BACKUP)

    source = source.replace(
        '[ValidateSet("Ekle", "Listele", "Dogrula")]',
        '[ValidateSet("Ekle", "Listele", "Dogrula", "Sil")]',
        1,
    )

    old_params = (
        '    [Parameter(Mandatory = $false)]\n'
        '    [string]$SourceReference\n'
        ')'
    )
    new_params = (
        '    [Parameter(Mandatory = $false)]\n'
        '    [string]$SourceReference,\n\n'
        '    [Parameter(Mandatory = $false)]\n'
        '    [string]$DeleteSymbol,\n\n'
        '    [Parameter(Mandatory = $false)]\n'
        '    [string]$DeleteSourceReference\n'
        ')'
    )

    if old_params in source:
        source = source.replace(old_params, new_params, 1)
    elif "$DeleteSymbol" not in source:
        fail("Parametre bölümü bulunamadı.")

    anchor = 'if ($Islem -eq "Dogrula") {\n'

    delete_block = r'''if ($Islem -eq "Sil") {
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

'''

    if anchor in source and 'if ($Islem -eq "Sil")' not in source:
        source = source.replace(anchor, delete_block + anchor, 1)
    elif 'if ($Islem -eq "Sil")' not in source:
        fail("Dogrula bölümü bulunamadı.")

    TARGET.write_text(source, encoding="utf-8-sig", newline="\n")
    print("Sprint-41 VBTS kayıt silme desteği eklendi.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
