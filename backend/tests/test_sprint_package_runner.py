from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "Sprint-Paketini-Kur-ve-Test-Et.ps1"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8-sig")


def test_tek_komut_betigi_mevcut() -> None:
    assert SCRIPT.exists()


def test_hizli_ve_tam_modlarini_destekler() -> None:
    source = _source()

    assert '"Hizli", "Tam"' in source
    assert '$Mod = "Hizli"' in source
    assert 'if ($Mod -eq "Tam")' in source


def test_zip_paketi_cikarabilir() -> None:
    source = _source()

    assert "Expand-Archive" in source
    assert "$Paket" in source


def test_yalnizca_paket_icindeki_apply_yamalarini_bulur() -> None:
    source = _source()

    assert '[System.IO.Compression.ZipFile]::OpenRead' in source
    assert '$_.Name -like "apply_*.py"' in source
    assert "$PackagePatchPaths" in source
    assert "python $PatchPath" in source


def test_hedef_ve_tam_testleri_calistirabilir() -> None:
    source = _source()

    assert "python -m pytest $HedefTest -q" in source
    assert "python -m pytest -q" in source


def test_hata_durumunda_islemi_durdurur() -> None:
    source = _source()

    assert "$LASTEXITCODE -ne 0" in source
    assert "exit 1" in source
