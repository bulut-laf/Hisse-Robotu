from pathlib import Path
from backend.app.news_center.v1_release import NEWS_CENTER_V1_OFFICIAL_SOURCES
from backend.app.ui.official_source_feed_renderer import official_source_feed_ui_names
DASHBOARD=Path('backend/app/ui/news_center_dashboard.py'); VERIFY_SCRIPT=Path('backend/scripts/verify_news_center_v1.py'); RELEASE_DOC=Path('HABER_MERKEZI_V1_RELEASE.md')
def test_sprint178_dashboard_v1_version_importu(): assert 'NEWS_CENTER_V1_VERSION' in DASHBOARD.read_text(encoding='utf-8')
def test_sprint178_dashboard_basligi(): assert 'Sprint-178 Kararlı Sürüm ve Tam Sistem Doğrulaması' in DASHBOARD.read_text(encoding='utf-8')
def test_feed_ui_backend_source_manifesti_ayni(): assert official_source_feed_ui_names()==NEWS_CENTER_V1_OFFICIAL_SOURCES
def test_v1_14_sekme_korunur():
    t=DASHBOARD.read_text(encoding='utf-8')
    for x in ('Günlük Operasyon','Kaynak Besleme','Son Dakika','Bugünün Önemli Gelişmeleri','Gün Sonu Özeti','Ekonomik Takvim','KAP Akışı','Hisse Haberleri','Manuel Haber Ekle','Olay Arşivi','Etki Bağlantıları','Sektör Etki Haritası','Portföy Etki Radarı','Haber Arşivi'): assert f'"{x}"' in t
def test_v1_dashboard_polling_yasagi_korunur():
    t=DASHBOARD.read_text(encoding='utf-8'); assert 'otomatik polling' in t and 'toplu scraping' in t
def test_v1_dashboard_ai_karar_yasagi_korunur():
    t=DASHBOARD.read_text(encoding='utf-8'); assert 'AI değerlendirmesi yapmaz' in t and 'teknik analiz skorlarını' in t
def test_v1_verify_script_ag_kullanmaz():
    t=VERIFY_SCRIPT.read_text(encoding='utf-8').casefold(); assert 'urlopen' not in t and 'requests.' not in t and 'httpx.' not in t
def test_v1_verify_script_basarili_cikti_var(): assert 'HABER MERKEZİ V{NEWS_CENTER_V1_VERSION} SİSTEM KONTROLÜ BAŞARILI' in VERIFY_SCRIPT.read_text(encoding='utf-8')
def test_v1_release_doc_var():
    t=RELEASE_DOC.read_text(encoding='utf-8'); assert 'Haber Merkezi V1.0.0 Kararlı Sürüm' in t and 'Sprint-149–178' in t
def test_v1_release_doc_sinirlar_var():
    t=RELEASE_DOC.read_text(encoding='utf-8'); assert 'otomatik polling yapmaz' in t and 'AL/SAT üretmez' in t and 'Şirket Yatırımcı İlişkileri' in t
def test_v1_eski_streamlit_api_yok(): assert 'use_container_width' not in DASHBOARD.read_text(encoding='utf-8')
