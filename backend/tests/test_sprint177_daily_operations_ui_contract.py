from pathlib import Path


DASHBOARD = Path("backend/app/ui/news_center_dashboard.py")
PANEL = Path("backend/app/ui/daily_news_operations_panel.py")


def test_sprint177_basligi_var():
    assert "Sprint-177" in DASHBOARD.read_text(encoding="utf-8")


def test_gunluk_operasyon_ilk_tab():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "daily_operations_tab," in text
    assert '"Günlük Operasyon",' in text
    assert text.index('"Günlük Operasyon",') < text.index('"Kaynak Besleme",')


def test_panel_dashboarda_bagli():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "render_daily_news_operations_panel" in text
    assert "with daily_operations_tab:" in text


def test_panel_yeni_birlesik_skor_uretmedigini_aciklar():
    text = PANEL.read_text(encoding="utf-8")
    assert "Yeni birleşik skor" in text
    assert "AL/SAT" in text
    assert "AI yorumu" in text


def test_panel_maksimum_arsiv_limitleriyle_okur():
    text = PANEL.read_text(encoding="utf-8")
    assert "archive.list_events(limit=5000)" in text
    assert "archive.list_news(limit=10000)" in text


def test_panel_operasyon_gecmisini_okur():
    text = PANEL.read_text(encoding="utf-8")
    assert "OfficialSourceOperationStore" in text
    assert "store.read(limit=5000)" in text


def test_panel_golge_portfoy_acik_pozisyonlari_kullanir():
    text = PANEL.read_text(encoding="utf-8")
    assert "ShadowPortfolioStore().list()" in text
    assert "item.status == OPEN_STATUS" in text


def test_panel_temel_metrikler_var():
    text = PANEL.read_text(encoding="utf-8")
    for label in ('"Olay"','"Haber"','"Önem ≥80"','"KAP olayı"','"Hisse"','"Portföy teması"','"Kullanılan resmî kaynak"','"Kaynak operasyonu"','"Operasyon hatası"','"Birincil haber"'):
        assert label in text


def test_panel_oncelikli_olaylar_var():
    text = PANEL.read_text(encoding="utf-8")
    assert 'st.subheader("Günün öncelikli olayları")' in text
    assert "daily_operations_event_rows" in text


def test_panel_resmi_kaynak_gorunumu_var():
    text = PANEL.read_text(encoding="utf-8")
    assert 'st.subheader("Resmî kaynak günlük görünümü")' in text
    assert "daily_operations_source_rows" in text


def test_panel_yeni_ag_istegi_atmadigini_aciklar():
    text = PANEL.read_text(encoding="utf-8")
    assert "yeni ağ " in text
    assert "isteği göndermez" in text


def test_dashboard_polling_yasagi_korunur():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert "otomatik polling" in text
    assert "toplu scraping" in text


def test_eski_kaynak_besleme_sekmesi_korunur():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert '"Kaynak Besleme"' in text
    assert "render_official_source_feed_blocks" in text


def test_eski_gun_sonu_ve_kap_sekmeleri_korunur():
    text = DASHBOARD.read_text(encoding="utf-8")
    assert '"Gün Sonu Özeti"' in text
    assert '"KAP Akışı"' in text


def test_streamlit_eski_api_yok():
    text = DASHBOARD.read_text(encoding="utf-8") + PANEL.read_text(encoding="utf-8")
    assert "use_container_width" not in text
    assert 'width="stretch"' in text
