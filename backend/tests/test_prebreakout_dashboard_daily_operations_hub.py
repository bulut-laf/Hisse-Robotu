from pathlib import Path


SOURCE = Path("backend/app/ui/prebreakout_dashboard.py")


def _source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_dashboard_gunluk_operasyon_merkezini_icerir() -> None:
    source = _source()
    assert '"Günlük Operasyon Merkezi"' in source
    assert "_render_daily_operations_hub(existing_live_signals)" in source


def test_dashboard_gunluk_operasyon_temel_metriklerini_icerir() -> None:
    source = _source()
    assert '"Toplam canlı aday"' in source
    assert '"Bugünkü yeni aday"' in source
    assert '"E3–E4 güçlü hazırlık"' in source
    assert '"E2 izleme"' in source


def test_dashboard_gunluk_islem_sirasini_gosterir() -> None:
    source = _source()
    assert '"Günlük işlem sırası"' in source
    assert "Tarama ve yeni E2–E4 kayıtları" in source
    assert "5/10/20 günlük gerçek sonuçlar" in source


def test_dashboard_tek_ekranda_ana_operasyon_bolumlerini_adlandirir() -> None:
    source = _source()
    for label in (
        "Canlı adaylar",
        "Yaşam döngüsü",
        "Gerçek sonuçlar",
        "Deneme portföyü",
        "Sistem sağlığı",
    ):
        assert label in source
