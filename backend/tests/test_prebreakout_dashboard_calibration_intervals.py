from pathlib import Path


def test_dashboard_guven_araligi_karar_destegini_icerir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert "asama_guven_araliklarini_hesapla(" in source
    assert "temkinli_lider_asamayi_sec(" in source
    assert '"Temkinli lider:' in source
    assert '"Aşama başarı oranı güven aralıkları"' in source
    assert '"Güven aralıklarını CSV indir"' in source
