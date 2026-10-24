from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def test_active_trader_importu_dashboarda_baglidir():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert "from backend.app.analysis.active_shadow_trader import (" in source
    assert "assess_shadow_position" in source
    assert "ActiveShadowTraderStore" in source


def test_golge_portfoyde_aktif_trader_sekmesi_vardir():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert '"Aktif Trader Yönetimi"' in source
    assert "with trader_tab:" in source


def test_manual_gun_ici_fiyat_ve_stop_uygulama_akisi_vardir():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert '"Manuel gün içi fiyat"' in source
    assert '"Önerilen stopu aktif stop olarak kaydet"' in source
    assert '"Trader değerlendirmesini kaydet"' in source


def test_stop_cikis_butonu_kullanici_onayi_ister():
    source = DASHBOARD.read_text(encoding="utf-8-sig")
    assert '"Bu fiyatla pozisyonu kapat"' in source
    assert "close_shadow_position(" in source
