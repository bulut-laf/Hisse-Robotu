from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "VBTS-Hizli-Hazirla.ps1"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8-sig")


def test_sil_islemi_desteklenir() -> None:
    source = _source()
    assert '"Ekle", "Listele", "Dogrula", "Sil"' in source
    assert 'if ($Islem -eq "Sil")' in source


def test_silme_sembol_ve_kaynak_referansi_ile_yapilir() -> None:
    source = _source()
    assert "$DeleteSymbol" in source
    assert "$DeleteSourceReference" in source
    assert "Silinecek hisse sembolü" in source
    assert "Silinecek kaynak referansı" in source


def test_silme_sonrasi_csv_yeniden_yazilir() -> None:
    source = _source()
    assert "$RemainingRows" in source
    assert "Export-Csv -LiteralPath $CsvPath" in source
    assert "Remove-Item -LiteralPath $CsvPath" in source


def test_eslesen_kayit_yoksa_hata_verir() -> None:
    assert "Silinecek kayıt bulunamadı." in _source()


def test_silme_sonrasi_kalan_kayit_sayisi_gosterilir() -> None:
    source = _source()
    assert "VBTS kaydı silindi." in source
    assert "Kalan kayıt sayısı:" in source
