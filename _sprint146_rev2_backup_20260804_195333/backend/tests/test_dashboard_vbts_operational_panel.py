from pathlib import Path


def test_dashboard_otomatik_senkronizasyonu_cagirir() -> None:
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "synchronize_vbts_operational_state(csv_path)" in source


def test_dashboard_senkronizasyon_hatasinda_kilit_mesaji_gosterir() -> None:
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "Toplu tarama güvenlik nedeniyle kilitli" in source


def test_dashboard_son_senkronizasyonu_ve_son_islemi_gosterir() -> None:
    source = Path("backend/dashboard.py").read_text(encoding="utf-8")
    assert "Son otomatik senkronizasyon" in source
    assert "Son VBTS işlemi" in source
    assert "Denetim günlüğü" in source
