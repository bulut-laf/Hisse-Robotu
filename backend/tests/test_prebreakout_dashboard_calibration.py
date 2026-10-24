from pathlib import Path


def test_dashboard_kalibrasyon_bolumunu_icerir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(
        encoding="utf-8"
    )

    assert 'st.subheader("Ön Yükseliş Kalibrasyonu")' in source
    assert "asama_kalibrasyonunu_hesapla(replay_results)" in source
    assert "momentum_kalibrasyonunu_hesapla(replay_results)" in source
    assert "üretim eşikleri otomatik değiştirilmez" in source
