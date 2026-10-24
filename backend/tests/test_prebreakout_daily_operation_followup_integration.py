from pathlib import Path


def test_gunluk_operasyon_alarm_ve_karar_takibini_otomatik_cagirir() -> None:
    source = Path("backend/app/prebreakout/prebreakout_daily_operation.py").read_text(encoding="utf-8")
    assert "gunluk_operasyon_takibini_guncelle(" in source
    assert source.count("gunluk_operasyon_takibini_guncelle(") >= 4
    assert "alarm_history_path:" in source
    assert "decision_journal_path:" in source
    assert "DEFAULT_ALARM_HISTORY_PATH" in source
    assert "DEFAULT_DECISION_JOURNAL_PATH" in source


def test_sprint104_arsiv_uyumlulugu_korunur() -> None:
    source = Path("backend/app/prebreakout/prebreakout_daily_operation.py").read_text(encoding="utf-8")
    assert "DEFAULT_OPERATION_ARCHIVE_PATH" in source
    assert "gunluk_operasyon_arsiv_kaydi_olustur(" in source
    assert source.count("gunluk_operasyon_arsivini_kaydet(") >= 4
