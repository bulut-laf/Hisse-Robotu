from pathlib import Path


def _source() -> str:
    return Path("backend/dashboard.py").read_text(encoding="utf-8")


def test_dashboard_yedekleri_listeler_ve_onizler() -> None:
    source = _source()
    assert "list_vbts_backups" in source
    assert "inspect_vbts_backup" in source
    assert "Geri yüklenecek VBTS yedeği" in source


def test_dashboard_acik_onayla_geri_yukler() -> None:
    source = _source()
    assert "Onaylamak için GERİ YÜKLE yazın" in source
    assert "restore_vbts_backup" in source
    assert "Seçilen VBTS yedeğini geri yükle" in source


def test_dashboard_denetim_gunlugunu_tabloda_gosterir() -> None:
    source = _source()
    assert "Son denetim işlemleri" in source
    assert "audit_display_rows" in source


def test_dashboard_geri_yukleme_hatasinda_uyari_modunu_korur() -> None:
    source = _source()
    assert "VBTS yedeği geri yüklenemedi" in source
    assert "Toplu tarama VBTS uyarı modunda devam edebilir" in source
