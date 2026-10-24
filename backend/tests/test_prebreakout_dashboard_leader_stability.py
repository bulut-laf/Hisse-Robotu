from pathlib import Path


def test_dashboard_lider_kararliligi_karar_destegini_icerir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert "lider_kararlilik_ozetini_hesapla(" in source
    assert "lider_duyarlilik_senaryolarini_hesapla(" in source
    assert '"Temkinli lider kararlılığı"' in source
    assert '"Lider korunma oranı"' in source
    assert '"Kararlı" if stability_summary.stable else "Kırılgan"' in source
    assert '"Lider duyarlılık senaryolarını CSV indir"' in source
