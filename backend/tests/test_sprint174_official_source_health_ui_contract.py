from pathlib import Path


UI = Path("backend/app/ui/news_center_dashboard.py")


def source():
    return UI.read_text(encoding="utf-8")


def test_health_modulu_uiya_baglanir():
    text = source()
    assert "from backend.app.news_center.official_source_health import (" in text
    assert "diagnose_official_source_adapters" in text
    assert "official_source_adapter_names" in text


def test_aktif_adapter_listesi_merkezi_kayittan_gelir():
    text = source()
    assert "active_adapter_names = official_source_adapter_names()" in text
    assert "feed_source_statuses((*active_adapter_names,))" in text


def test_aktif_adapter_sayisi_hardcode_degil():
    text = source()
    assert 'metric("Aktif adapter", len(active_adapter_names))' in text
    assert 'metric("Aktif adapter", 7)' not in text


def test_yapisal_saglik_ozeti_var():
    text = source()
    assert 'st.subheader("Resmî adapter yapısal sağlığı")' in text
    assert '"Yapısal sağlık"' in text
    assert '"Kontroller"' in text


def test_canli_ag_testi_yok_mesaji_var():
    text = source()
    assert '"Canlı ağ testi", "YOK"' in text
    assert "canlı internet erişilebilirliği anlamına gelmez" in text


def test_ag_varsayilan_kapali_gosterilir():
    text = source()
    assert '"Varsayılan ağ", "KAPALI"' in text


def test_health_tablosu_hazir_hata_gosterir():
    text = source()
    assert '"Durum": "HAZIR" if row.ready else "HATA"' in text
    assert '"Kontrol": f"{row.passed_count}/{row.check_count}"' in text


def test_health_hatasi_ui_warning_uretir():
    text = source()
    assert "Yapısal tanılamada hata bulunan adapterler var." in text
    assert "health_status.issues" in text


def test_polling_ve_scraping_acilmadi():
    text = source()
    assert "otomatik polling yapmaz" in text
    assert "toplu sorgu veya arka plan taraması yapmaz" in text


def test_sprint174_basligi_var():
    assert "Sprint-174" in source()


def test_eski_streamlit_api_yok():
    text = source()
    assert "use_container_width" not in text
    assert 'width="stretch"' in text
