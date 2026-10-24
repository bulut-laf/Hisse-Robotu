from pathlib import Path


def test_gunluk_operasyon_terminal_sonuclari_arsivlenir() -> None:
    source = Path("backend/app/prebreakout/prebreakout_daily_operation.py").read_text(encoding="utf-8")
    assert "DEFAULT_OPERATION_ARCHIVE_PATH" in source
    assert "archive_path:" in source
    assert "gunluk_operasyon_arsiv_kaydi_olustur(" in source
    assert source.count("gunluk_operasyon_arsivini_kaydet(") >= 4
