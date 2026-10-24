import re
from backend.app.news_center.models import SourceTier
from backend.app.news_center.official_source_health import diagnose_official_source_adapters
from backend.app.news_center.official_source_operations import OfficialSourceOperationKind
from backend.app.news_center.source_registry import resolve_source
from backend.app.news_center.v1_release import NEWS_CENTER_V1_CAPABILITIES, NEWS_CENTER_V1_GUARDRAILS, NEWS_CENTER_V1_OFFICIAL_SOURCES, NEWS_CENTER_V1_VERSION, validate_news_center_v1_backend

def test_v1_version(): assert NEWS_CENTER_V1_VERSION=='1.0.0'
def test_v1_version_semver(): assert re.fullmatch(r'\d+\.\d+\.\d+',NEWS_CENTER_V1_VERSION)
def test_v1_yedi_resmi_kaynak(): assert NEWS_CENTER_V1_OFFICIAL_SOURCES==('KAP','TCMB','TÜİK','SPK','Hazine ve Maliye Bakanlığı','Borsa İstanbul','Resmî Gazete')
def test_v1_resmi_kaynak_sayisi_yedi(): assert len(NEWS_CENTER_V1_OFFICIAL_SOURCES)==7
def test_v1_tum_resmi_kaynaklar_tier1():
    for name in NEWS_CENTER_V1_OFFICIAL_SOURCES:
        r=resolve_source(name); assert r is not None and r.canonical_name==name and r.tier is SourceTier.TIER_1_OFFICIAL
def test_v1_sirket_ir_aktif_adapter_listesinde_degil(): assert 'Şirket Yatırımcı İlişkileri' not in NEWS_CENTER_V1_OFFICIAL_SOURCES
def test_v1_capability_manifest_genisligi(): assert len(NEWS_CENTER_V1_CAPABILITIES)>=17
def test_v1_capability_manifest_gunluk_operasyon_var(): assert 'Günlük Haber Merkezi Operasyon ekranı' in NEWS_CENTER_V1_CAPABILITIES
def test_v1_capability_manifest_kap_akisi_var(): assert 'KAP Akışı' in NEWS_CENTER_V1_CAPABILITIES
def test_v1_capability_manifest_arsiv_var(): assert 'Gelişmiş Haber Arşivi' in NEWS_CENTER_V1_CAPABILITIES
def test_v1_guardrail_manifest_genisligi(): assert len(NEWS_CENTER_V1_GUARDRAILS)>=10
def test_v1_guardrail_polling_yasagi(): assert any('polling yoktur' in x for x in NEWS_CENTER_V1_GUARDRAILS)
def test_v1_guardrail_al_sat_yasagi(): assert any('AL/SAT' in x for x in NEWS_CENTER_V1_GUARDRAILS)
def test_v1_guardrail_teknik_skor(): assert any('teknik analiz skorunu' in x for x in NEWS_CENTER_V1_GUARDRAILS)
def test_v1_operation_kinds_tam(): assert {x.value for x in OfficialSourceOperationKind}=={'PREVIEW_BLOCKED','PREVIEW_SUCCESS','PREVIEW_ERROR','ARCHIVE_SUCCESS','ARCHIVE_DUPLICATE','ARCHIVE_ERROR'}
def test_v1_health_yedi_adapter(): assert len(diagnose_official_source_adapters())==7
def test_v1_health_tumu_hazir(): assert all(x.ready for x in diagnose_official_source_adapters())
def test_v1_health_49_49():
    h=diagnose_official_source_adapters(); assert sum(x.check_count for x in h)==49; assert sum(x.passed_count for x in h)==49
def test_v1_health_ag_probe_yok(): assert all(x.network_probe_performed is False for x in diagnose_official_source_adapters())
def test_v1_backend_status_ready(): assert validate_news_center_v1_backend().ready is True
def test_v1_backend_status_version(): assert validate_news_center_v1_backend().version=='1.0.0'
def test_v1_backend_status_failure_yok(): assert validate_news_center_v1_backend().failures==()
def test_v1_backend_status_tum_kontroller_gecer():
    s=validate_news_center_v1_backend(); assert s.passed_count==s.check_count
def test_v1_backend_kontrol_sayisi_11(): assert validate_news_center_v1_backend().check_count==11
