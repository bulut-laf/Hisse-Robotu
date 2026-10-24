from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "data" / "vbts" / "vbts_sablon.csv"
ACTIVE_CSV = ROOT / "data" / "vbts" / "vbts_guncel.csv"
CONFIG_SCRIPT = ROOT / "VBTS-Manuel-Kaynak-Ayarla.ps1"
GUIDE = ROOT / "docs" / "VBTS_MANUEL_CSV_KULLANIMI.md"
EXPECTED_HEADER = "symbol,measure_type,start_date,end_date,source_reference"


def test_vbts_csv_sablonu_gerekli_basliklari_icerir() -> None:
    assert TEMPLATE.exists()

    lines = TEMPLATE.read_text(encoding="utf-8-sig").splitlines()

    assert lines == [EXPECTED_HEADER]


def test_bos_sablon_bilerek_aktif_veri_dosyasi_degildir() -> None:
    """Şablon ile çalışma anında üretilen aktif CSV ayrı varlıklardır.

    Bu test, kullanıcının gerçek ve doğrulanmış VBTS kaydı eklemiş olabileceği
    çalışma ortamında da geçerli olmalıdır. Aktif CSV'nin varlığı/olmaması bir
    kurulum varlığı testi değildir; yalnızca şablonun boş ve ayrı olması
    doğrulanır.
    """

    assert TEMPLATE.name == "vbts_sablon.csv"
    assert ACTIVE_CSV.name == "vbts_guncel.csv"
    assert TEMPLATE.resolve() != ACTIVE_CSV.resolve()
    assert TEMPLATE.read_text(encoding="utf-8-sig").splitlines() == [EXPECTED_HEADER]


def test_yapilandirma_betigi_manual_csv_kaynagini_tanimlar() -> None:
    assert CONFIG_SCRIPT.exists()

    source = CONFIG_SCRIPT.read_text(encoding="utf-8-sig")

    assert "HISSE_ROBOTU_VBTS_SOURCE" in source
    assert "manual_csv" in source
    assert "HISSE_ROBOTU_VBTS_CSV_PATH" in source
    assert "HISSE_ROBOTU_VBTS_CSV_MAX_AGE_HOURS" in source
    assert "vbts_guncel.csv" in source


def test_yapilandirma_betigi_olmayan_ve_bos_dosyayi_reddeder() -> None:
    source = CONFIG_SCRIPT.read_text(encoding="utf-8-sig")

    assert "Test-Path" in source
    assert "Import-Csv" in source
    assert "Count" in source
    assert "kayıt içermiyor" in source


def test_kullanim_kilavuzu_resmi_kaynak_zorunlulugunu_aciklar() -> None:
    assert GUIDE.exists()

    source = GUIDE.read_text(encoding="utf-8-sig")

    assert "resmî KAP" in source
    assert "vbts_sablon.csv" in source
    assert "vbts_guncel.csv" in source
    assert "VBTS-Manuel-Kaynak-Ayarla.ps1" in source
    assert "yatırım tavsiyesi değildir" in source
