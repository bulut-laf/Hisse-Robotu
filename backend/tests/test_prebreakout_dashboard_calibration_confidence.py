from pathlib import Path


def test_dashboard_kalibrasyon_guven_kontrollerini_icerir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(
        encoding="utf-8"
    )

    assert '"Güvenilir aşama için minimum ölçüm"' in source
    assert "kalibrasyon_ozetini_hesapla(" in source
    assert '"Ölçüm kapsamı"' in source
    assert '"Yalnızca yeterli örneklemli aşamaları göster"' in source
    assert '"Aşama kalibrasyonunu CSV indir"' in source
    assert '"Momentum kalibrasyonunu CSV indir"' in source
