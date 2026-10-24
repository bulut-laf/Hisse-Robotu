from pathlib import Path


def _source() -> str:
    return Path("backend/dashboard.py").read_text(encoding="utf-8")


def test_dashboard_vbts_sistem_sagligini_gosterir() -> None:
    source = _source()
    assert "VBTS sistem sağlığı" in source
    assert "validate_vbts_system_health" in source


def test_dashboard_yedek_butunlugunu_gosterir() -> None:
    assert '"Yedek bütünlüğü"' in _source()


def test_dashboard_denetim_gunlugunu_csv_indirir() -> None:
    source = _source()
    assert "Denetim günlüğünü CSV indir" in source
    assert "audit_events_csv_bytes" in source


def test_dashboard_yedek_temizleme_politikasi_sunar() -> None:
    source = _source()
    assert "Yedek bakım politikası" in source
    assert "Eski VBTS yedeklerini temizle" in source
    assert "prune_vbts_backups" in source


def test_dashboard_butunluk_hatasinda_uyari_modunu_korur() -> None:
    source = _source()
    assert "VBTS sistem sağlığı: Sorunlu" in source
    assert "Toplu tarama VBTS uyarı modunda devam edebilir" in source
