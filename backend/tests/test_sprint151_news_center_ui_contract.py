from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")


def _source() -> str:
    return UI.read_text(encoding="utf-8-sig")


def test_ui_deterministik_classifier_import_ediyor():
    source = _source()
    assert "from backend.app.news_center.classifier import classify_news" in source


def test_ui_onizleme_ve_otomatik_uygulama_kontrolu_var():
    source = _source()
    assert "Deterministik sınıflandırmayı önizle" in source
    assert "Deterministik sınıflandırmayı kayıtta uygula" in source
    assert "classification.source_tier or manual_source_tier" in source


def test_ui_ai_ve_teknik_skoru_siniflandirma_girdisi_yapmaz():
    source = _source().casefold()
    classifier_call_start = source.index("classification = classify_news(")
    classifier_call_end = source.index(")", classifier_call_start)
    call = source[classifier_call_start:classifier_call_end]
    assert "ai_score" not in call
    assert "technical_score" not in call
    assert "signal" not in call
