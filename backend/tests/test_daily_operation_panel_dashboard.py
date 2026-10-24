from __future__ import annotations

import ast
from pathlib import Path


DASHBOARD = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD.read_text(encoding="utf-8-sig")


def test_gunluk_operasyon_paneli_analiz_moduna_eklenmistir():
    text = source()

    assert '"Günlük Operasyon Paneli"' in text
    assert "gunluk_operasyon_paneli_formu" in text


def test_panel_veri_sinyal_ve_islem_kayitlarini_birlestirir():
    text = source()

    assert "DelayedDataPilotStore" in text
    assert "SignalOutcomeJsonStore" in text
    assert "TradeJournalStore" in text
    assert "build_daily_operation_summary" in text


def test_panel_kritik_uyari_ve_gunluk_gorevleri_gosterir():
    text = source()

    assert "Kritik uyarılar" in text
    assert "Bugünkü yapılacak işlemler" in text
    assert "alert_rows" in text
    assert "task_rows" in text


def test_panel_yenileme_dugmesi_stretch_kullanir():
    text = source()

    assert '"Operasyon panelini yenile"' in text
    assert 'width="stretch"' in text


def test_dashboard_sozdizimi_gecerlidir():
    ast.parse(source())


def test_gunluk_operasyon_paneli_v11_rolu_aciktir():
    text = source()

    assert '"Günlük Operasyon Paneli — Sistem ve Görev Özeti"' in text
    assert "yeni teknik skor, işlem sinyali veya AL/SAT kararı üretmez" in text
    assert '"#### Operasyon özeti"' in text
    assert '"#### Öncelikli operasyon uyarıları"' in text
    assert '"#### Bugünkü görevler ve hedef modül"' in text
    assert '"#### Modül yönlendirmesi"' in text


def test_gunluk_operasyon_paneli_v11_modul_yonlendirmelerini_korur():
    text = source()

    assert "Gecikmeli Veri Pilotu" in text
    assert "BIST Toplu Tarama" in text
    assert "Fırsat Radarı" in text
    assert "Güncel Teknik Analiz" in text
    assert "Sinyal Sonuçları" in text
    assert "Gölge Portföy" in text
    assert '"Operasyon panelini yenile"' in text
