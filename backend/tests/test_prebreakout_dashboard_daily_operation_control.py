from pathlib import Path


def test_dashboard_tek_tus_ve_guvenli_yeniden_deneme_durumunu_gosterir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert '"Tek tuş günlük operasyon"' in source
    assert "gunluk_operasyon_durumunu_yukle()" in source
    assert '"Günlük operasyon tamamlandı"' in source
    assert '"Günlük operasyon sağlık kilidinde"' in source
    assert '"Günlük operasyon güvenli yeniden denemeye hazır"' in source
