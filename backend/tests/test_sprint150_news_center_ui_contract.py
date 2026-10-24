from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")
ARCHIVE = Path("backend/app/news_center/archive.py")


def test_bos_arsivde_mevcut_olaya_bagla_secenegi_sunulmaz():
    source = UI.read_text(encoding="utf-8")
    assert 'if events\n            else ("Yeni olay oluştur",)' in source
    assert "Bağlanabilecek olay yok. Önce yeni bir olay kaydı oluşturun." not in source


def test_sprint150_ozet_metrikleri_var():
    source = UI.read_text(encoding="utf-8")
    for label in ("Olay", "Haber", "Önem ≥80", "Çok kaynaklı olay"):
        assert label in source


def test_olay_detayi_bagli_kaynaklari_gosterir():
    source = UI.read_text(encoding="utf-8")
    assert '"Olay detayı"' in source
    assert "archive.list_news_for_event(detail_event_id)" in source
    assert "Bağlı haber kaynakları" in source


def test_archive_olay_bazli_haber_okuma_api_sunar():
    source = ARCHIVE.read_text(encoding="utf-8")
    assert "def list_news_for_event(" in source
    assert "WHERE event_id = ?" in source
    assert "ORDER BY published_at ASC, archived_at ASC" in source


def test_ui_teknik_karar_motoruna_dokunmaz():
    source = UI.read_text(encoding="utf-8").casefold()
    forbidden = (
        "technical_score",
        "buy_signal",
        "sell_signal",
        "signal_engine",
        "risk_engine",
        "candidate_rank",
    )
    for token in forbidden:
        assert token not in source
