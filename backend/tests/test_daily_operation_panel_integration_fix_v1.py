from pathlib import Path


def test_daily_operation_panel_auto_scan_and_non_blocking_contract():
    dashboard = Path("backend/dashboard.py").read_text(encoding="utf-8")
    panel = Path("backend/app/analysis/daily_operation_panel.py").read_text(encoding="utf-8")

    assert 'evren="BIST 100"' in dashboard
    assert 'profil_adi=TARAMA_PROFILLERI["Dengeli"]' in dashboard
    assert "Günlük karar listesi için BIST 100 otomatik taranıyor" in dashboard
    assert "manuel tarama zorunlu değildir" in dashboard
    assert "AL / BEKLE / İŞLEM YOK closeout" in dashboard
    assert "Eski/gecikmeli veri — son geçerli veriyle devam" in panel
    assert "Veri eski/gecikmeli — operasyon devam ediyor" in panel
    assert "Sabah aday sunumu bloklu" not in dashboard
