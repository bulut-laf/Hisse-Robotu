from pathlib import Path

from backend.app.ui.official_source_feed_renderer import (
    OFFICIAL_SOURCE_FEED_UI_SPECS,
    official_source_feed_ui_names,
)


EXPECTED_NAMES = (
    "KAP",
    "TCMB",
    "TÜİK",
    "SPK",
    "Hazine ve Maliye Bakanlığı",
    "Borsa İstanbul",
    "Resmî Gazete",
)


def test_yedi_ui_speci_var():
    assert len(OFFICIAL_SOURCE_FEED_UI_SPECS) == 7


def test_ui_spec_isimleri_beklenen_sirada():
    assert official_source_feed_ui_names() == EXPECTED_NAMES


def test_sluglar_benzersiz():
    slugs = tuple(spec.slug for spec in OFFICIAL_SOURCE_FEED_UI_SPECS)
    assert len(set(slugs)) == len(slugs)


def test_url_keyleri_benzersiz():
    keys = tuple(spec.url_key for spec in OFFICIAL_SOURCE_FEED_UI_SPECS)
    assert len(set(keys)) == len(keys)


def test_network_keyleri_benzersiz():
    keys = tuple(spec.network_key for spec in OFFICIAL_SOURCE_FEED_UI_SPECS)
    assert len(set(keys)) == len(keys)


def test_preview_state_keyleri_benzersiz():
    keys = tuple(spec.preview_state_key for spec in OFFICIAL_SOURCE_FEED_UI_SPECS)
    assert len(set(keys)) == len(keys)


def test_preview_button_keyleri_benzersiz():
    keys = tuple(spec.preview_button_key for spec in OFFICIAL_SOURCE_FEED_UI_SPECS)
    assert len(set(keys)) == len(keys)


def test_import_button_keyleri_benzersiz():
    keys = tuple(spec.import_button_key for spec in OFFICIAL_SOURCE_FEED_UI_SPECS)
    assert len(set(keys)) == len(keys)


def test_tum_adapter_ve_hata_tipleri_tanimli():
    for spec in OFFICIAL_SOURCE_FEED_UI_SPECS:
        assert isinstance(spec.adapter_type, type)
        assert isinstance(spec.error_type, type)
        assert issubclass(spec.error_type, RuntimeError)


def test_tum_url_alanlari_news_center_namespaceinde():
    for spec in OFFICIAL_SOURCE_FEED_UI_SPECS:
        assert spec.url_key.startswith("news_center_")
        assert spec.url_key.endswith("_feed_url")


def test_tum_ag_onaylari_news_center_namespaceinde():
    for spec in OFFICIAL_SOURCE_FEED_UI_SPECS:
        assert spec.network_key.startswith("news_center_")
        assert spec.network_key.endswith("_network_enabled")


def test_tum_preview_state_keyleri_news_center_namespaceinde():
    for spec in OFFICIAL_SOURCE_FEED_UI_SPECS:
        assert spec.preview_state_key.startswith("news_center_")
        assert spec.preview_state_key.endswith("_feed_preview")


def test_tum_ag_etiketleri_acik_onay_dilini_korur():
    for spec in OFFICIAL_SOURCE_FEED_UI_SPECS:
        assert "Bu işlem için" in spec.network_label
        assert "ağına bağlan" in spec.network_label


def test_tum_preview_dugmeleri_url_onizleme_dilini_korur():
    for spec in OFFICIAL_SOURCE_FEED_UI_SPECS:
        assert "URL'sini önizle" in spec.preview_button_label


def test_tum_import_dugmeleri_arsiv_dilini_korur():
    for spec in OFFICIAL_SOURCE_FEED_UI_SPECS:
        assert "arşive aktar" in spec.import_button_label


def test_tum_duplicate_mesajlari_mevcut_kaydi_belirtir():
    for spec in OFFICIAL_SOURCE_FEED_UI_SPECS:
        assert "arşivde" in spec.duplicate_preview_message
        assert "ikinci kez" in spec.duplicate_import_message


def test_tum_basari_mesajlari_acik_onayi_belirtir():
    for spec in OFFICIAL_SOURCE_FEED_UI_SPECS:
        assert "açık onayla" in spec.archive_success_message


def test_kap_ozel_summary_hisse_bilgisi_korur():
    spec = OFFICIAL_SOURCE_FEED_UI_SPECS[0]

    class Published:
        def astimezone(self, timezone):
            return self
        def strftime(self, fmt):
            return "2026-08-05 10:00:00"

    class Item:
        external_id = "123"
        published_at = Published()
        symbols = ("THYAO", "ASELS")

    assert spec.summary_formatter(Item(), object()) == (
        "KAP #123 · 2026-08-05 10:00:00 · THYAO, ASELS"
    )


def test_kap_duplicate_import_legacy_temizleme_davranisi_korunur():
    assert OFFICIAL_SOURCE_FEED_UI_SPECS[0].clear_after_duplicate_import is True
    assert all(
        spec.clear_after_duplicate_import is False
        for spec in OFFICIAL_SOURCE_FEED_UI_SPECS[1:]
    )


def test_dashboard_adapter_siniflarini_dogrudan_import_etmez():
    text = Path("backend/app/ui/news_center_dashboard.py").read_text(encoding="utf-8")
    for adapter in (
        "KapUrlAdapter",
        "TcmbPressUrlAdapter",
        "TuikPressUrlAdapter",
        "SpkPressUrlAdapter",
        "HmbPressUrlAdapter",
        "BorsaIstanbulAnnouncementUrlAdapter",
        "ResmiGazeteArticleUrlAdapter",
    ):
        assert adapter not in text


def test_dashboard_renderer_once_cagirir():
    text = Path("backend/app/ui/news_center_dashboard.py").read_text(encoding="utf-8")
    assert text.count("render_official_source_feed_blocks(st, archive, ISTANBUL)") == 1


def test_dashboard_kaynak_besleme_session_keylerini_tasimaz():
    text = Path("backend/app/ui/news_center_dashboard.py").read_text(encoding="utf-8")
    assert "news_center_kap_feed_preview" not in text
    assert "news_center_tcmb_feed_preview" not in text
    assert "news_center_resmi_gazete_feed_preview" not in text


def test_renderer_tek_ortak_block_fonksiyonu_kullanir():
    text = Path("backend/app/ui/official_source_feed_renderer.py").read_text(
        encoding="utf-8"
    )
    assert "def _render_source_feed_block(" in text
    assert "def render_official_source_feed_blocks(" in text
    assert "_render_source_feed_block(st, archive, timezone, spec, store)" in text


def test_renderer_ag_varsayilan_kapali_checkbox_korur():
    text = Path("backend/app/ui/official_source_feed_renderer.py").read_text(
        encoding="utf-8"
    )
    assert "value=False" in text


def test_renderer_dry_run_once_tanimlanir():
    text = Path("backend/app/ui/official_source_feed_renderer.py").read_text(
        encoding="utf-8"
    )
    assert text.count("FeedIngestionService(archive).preview(result.item)") == 1


def test_renderer_import_once_tanimlanir():
    text = Path("backend/app/ui/official_source_feed_renderer.py").read_text(
        encoding="utf-8"
    )
    assert text.count("FeedIngestionService(archive).import_item(preview_item)") == 1


def test_renderer_url_degisim_korumasi_once_tanimlanir():
    text = Path("backend/app/ui/official_source_feed_renderer.py").read_text(
        encoding="utf-8"
    )
    assert text.count(
        'str(source_url or "").strip() != str(preview_url or "").strip()'
    ) == 1


def test_renderer_eski_streamlit_api_kullanmaz():
    text = Path("backend/app/ui/official_source_feed_renderer.py").read_text(
        encoding="utf-8"
    )
    assert "use_container_width" not in text
    assert 'width="stretch"' in text
