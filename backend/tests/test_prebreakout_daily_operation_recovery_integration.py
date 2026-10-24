from pathlib import Path


def test_daily_operation_kurtarma_rehberini_kaydeder() -> None:
    source = Path("backend/app/prebreakout/prebreakout_daily_operation.py").read_text(encoding="utf-8")
    assert "operasyon_kurtarma_rehberi_olustur(" in source
    assert "operasyon_kurtarma_rehberini_kaydet(" in source
    assert "recovery_path:" in source
    assert source.count("operasyon_kurtarma_rehberini_kaydet(") >= 4
