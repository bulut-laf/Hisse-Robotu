from pathlib import Path


def test_dashboard_gunluk_operasyon_arsivini_icerir() -> None:
    source = Path("backend/app/ui/prebreakout_dashboard.py").read_text(encoding="utf-8")
    assert '"Günlük Operasyon Arşivi"' in source
    assert '"Yönetici özeti"' in source
    assert '"Geçmiş gün karşılaştırması"' in source
    assert "gunluk_operasyon_arsivini_yukle(" in source
    assert "yonetici_ozeti_olustur(" in source
