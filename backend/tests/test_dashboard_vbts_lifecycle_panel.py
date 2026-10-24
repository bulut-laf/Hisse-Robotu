from __future__ import annotations

from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def _source() -> str:
    return DASHBOARD.read_text(encoding="utf-8")


def test_dashboard_yasam_dongusu_fonksiyonlarini_import_eder() -> None:
    source = _source()
    assert "classify_vbts_records" in source
    assert "purge_expired_vbts_records" in source
    assert "sync_active_vbts_csv" in source


def test_dashboard_durum_ozetini_gosterir() -> None:
    source = _source()
    assert '"Aktif kayıt"' in source
    assert '"Gelecekte başlayacak"' in source
    assert '"Süresi dolmuş"' in source


def test_dashboard_suresi_dolmus_kayitlari_temizleyebilir() -> None:
    source = _source()
    assert "Süresi dolmuş kayıtları temizle" in source
    assert "Süresi dolmuş kayıtların kalıcı olarak silinmesini onaylıyorum." in source
