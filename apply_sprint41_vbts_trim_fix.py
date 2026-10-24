from __future__ import annotations

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "VBTS-Hizli-Hazirla.ps1"
BACKUP = TARGET.with_suffix(".ps1.sprint41-trim.bak")


def fail(message: str) -> None:
    print(f"HATA: {message}")
    raise SystemExit(1)


def main() -> None:
    if not TARGET.exists():
        fail(f"Dosya bulunamadı: {TARGET}")

    source = TARGET.read_text(encoding="utf-8-sig")
    shutil.copy2(TARGET, BACKUP)

    old_parse = '''    $Parsed = [datetime]::MinValue

    if (-not [datetime]::TryParseExact(
        $Value,
        "yyyy-MM-dd",'''
    new_parse = '''    $Parsed = [datetime]::MinValue
    $CleanValue = $Value.Trim()

    if (-not [datetime]::TryParseExact(
        $CleanValue,
        "yyyy-MM-dd",'''

    if old_parse in source:
        source = source.replace(old_parse, new_parse, 1)
    elif "$CleanValue = $Value.Trim()" not in source:
        fail("Tarih ayrıştırma bölümü bulunamadı.")

    old_dates = '''    $Start = Parse-IsoDate $StartDate "start_date"
    $End = Parse-IsoDate $EndDate "end_date"

    if ($End -lt $Start) {'''
    new_dates = '''    $Start = Parse-IsoDate $StartDate "start_date"
    $End = Parse-IsoDate $EndDate "end_date"
    $NormalizedStartDate = $Start.ToString("yyyy-MM-dd")
    $NormalizedEndDate = $End.ToString("yyyy-MM-dd")

    if ($End -lt $Start) {'''

    if old_dates in source:
        source = source.replace(old_dates, new_dates, 1)
    elif "$NormalizedStartDate" not in source:
        fail("Kayıt tarihi bölümü bulunamadı.")

    source = source.replace(
        '$_.start_date -eq $StartDate -and',
        '$_.start_date -eq $NormalizedStartDate -and',
    )
    source = source.replace(
        '$_.end_date -eq $EndDate -and',
        '$_.end_date -eq $NormalizedEndDate -and',
    )
    source = source.replace(
        'start_date = $StartDate',
        'start_date = $NormalizedStartDate',
    )
    source = source.replace(
        'end_date = $EndDate',
        'end_date = $NormalizedEndDate',
    )

    TARGET.write_text(source, encoding="utf-8-sig", newline="\n")
    print("Sprint-41 giriş boşluğu düzeltmesi uygulandı.")
    print(f"Yedek: {BACKUP}")


if __name__ == "__main__":
    main()
