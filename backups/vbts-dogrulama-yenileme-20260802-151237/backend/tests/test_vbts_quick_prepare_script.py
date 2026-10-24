from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "VBTS-Hizli-Hazirla.ps1"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8-sig")


def test_vbts_hizli_hazirlama_betigi_mevcut() -> None:
    assert SCRIPT.exists()


def test_ekle_listele_ve_dogrula_islemlerini_destekler() -> None:
    source = _source()

    assert '"Ekle", "Listele", "Dogrula"' in source
    assert '$Islem = "Dogrula"' in source


def test_gerekli_resmi_kayit_alanlarini_ister() -> None:
    source = _source()

    for field in (
        "$Symbol",
        "$MeasureType",
        "$StartDate",
        "$EndDate",
        "$SourceReference",
    ):
        assert field in source


def test_tarih_ve_sembol_dogrulamasi_yapar() -> None:
    source = _source()

    assert "TryParseExact" in source
    assert '"yyyy-MM-dd"' in source
    assert "Normalize-Symbol" in source
    assert "end_date, start_date tarihinden önce olamaz" in source


def test_bos_ve_yinelenen_kaydi_reddeder() -> None:
    source = _source()

    assert "kayıt içermiyor" in source
    assert "Aynı VBTS kaydı zaten mevcut" in source


def test_csv_yazar_ve_manual_kaynagi_etkinlestirir() -> None:
    source = _source()

    assert "Export-Csv" in source
    assert "HISSE_ROBOTU_VBTS_SOURCE" in source
    assert '"manual_csv"' in source
    assert "HISSE_ROBOTU_VBTS_CSV_PATH" in source


def test_sahte_ornek_piyasa_kaydi_icermez() -> None:
    source = _source()

    assert "THYAO" not in source
    assert "GARAN" not in source
    assert "AKBNK" not in source
