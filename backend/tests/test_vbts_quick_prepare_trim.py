from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "VBTS-Hizli-Hazirla.ps1"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8-sig")


def test_tarih_girdileri_trim_edilir() -> None:
    source = _source()

    assert "$CleanValue = $Value.Trim()" in source
    assert "$CleanValue," in source


def test_kaydedilen_tarihler_standart_bicime_cevrilir() -> None:
    source = _source()

    assert '$NormalizedStartDate = $Start.ToString("yyyy-MM-dd")' in source
    assert '$NormalizedEndDate = $End.ToString("yyyy-MM-dd")' in source
    assert "start_date = $NormalizedStartDate" in source
    assert "end_date = $NormalizedEndDate" in source


def test_yinelenen_kayit_karsilastirmasi_normalize_tarihleri_kullanir() -> None:
    source = _source()

    assert '$_.start_date -eq $NormalizedStartDate' in source
    assert '$_.end_date -eq $NormalizedEndDate' in source
