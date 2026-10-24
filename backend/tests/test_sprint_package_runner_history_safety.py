from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "Sprint-Paketini-Kur-ve-Test-Et.ps1"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8-sig")


def test_proje_kokundeki_tum_apply_dosyalarini_taramaz() -> None:
    source = _source()

    assert 'Get-ChildItem -LiteralPath $ProjectRoot -Filter "apply_*.py"' not in source


def test_paket_yoksa_eski_yamalari_calistirmayacagini_bildirir() -> None:
    source = _source()

    assert "Tarihî apply_*.py dosyaları yeniden çalıştırılmayacak." in source


def test_yalnizca_zip_icerisindeki_apply_dosyalarini_bulur() -> None:
    source = _source()

    assert "[System.IO.Compression.ZipFile]::OpenRead" in source
    assert '$_.Name -like "apply_*.py"' in source
    assert "$PackagePatchPaths" in source


def test_zip_cikarildiktan_sonra_sadece_paket_yamalarini_calistirir() -> None:
    source = _source()

    assert "foreach ($PatchPath in $PackagePatchPaths)" in source
    assert "python $PatchPath" in source


def test_paketsiz_tam_mod_sadece_regresyonu_calistirabilir() -> None:
    source = _source()

    assert 'if ($Mod -eq "Tam")' in source
    assert "python -m pytest -q" in source
