from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")
SERVICE = Path("backend/app/news_center/service.py")
GROUPING = Path("backend/app/news_center/grouping.py")
ARCHIVE = Path("backend/app/news_center/archive.py")
IMPORTANCE = Path("backend/app/news_center/importance.py")


def test_ui_sprint152_guvenli_eslestirme_kontrolunu_gosterir():
    source = UI.read_text(encoding="utf-8-sig")
    assert "Sprint-152" in source
    assert "Güvenli olay eşleştirmeyi kayıtta uygula" in source
    assert "EventGroupingReviewRequired" in source
    assert "Güvenli deterministik eşleşme ile mevcut olaya bağlandı." in source


def test_service_auto_group_varsayilani_geriye_uyumluluk_icin_false():
    source = SERVICE.read_text(encoding="utf-8-sig")
    assert "auto_group: bool = False" in source
    assert "best_event_match" in source
    assert "grouped_automatically" in source


def test_grouping_ai_ve_teknik_skor_kullanmaz():
    source = GROUPING.read_text(encoding="utf-8-sig").casefold()
    forbidden = (
        "gemini",
        "openai",
        "ai_score",
        "technical_score",
        "buy_signal",
        "sell_signal",
        "signal_engine",
    )
    for token in forbidden:
        assert token not in source


def test_sprint152_sqlite_semasi_ve_onem_formulunu_degistirmez():
    # Sprint-152 bu dosyaları paketlemeyecek; sözleşme testi çekirdek
    # davranışların hâlâ ayrı modüllerde kaldığını da doğrular.
    assert "CREATE TABLE IF NOT EXISTS events" in ARCHIVE.read_text(encoding="utf-8-sig")
    importance = IMPORTANCE.read_text(encoding="utf-8-sig")
    assert "SOURCE_SCORES" in importance
    assert "SCOPE_SCORES" in importance
    assert "EVENT_SCORES" in importance
