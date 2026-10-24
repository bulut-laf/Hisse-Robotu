from __future__ import annotations

from dataclasses import dataclass
import re

from .models import SourceTier
from .official_source_health import diagnose_official_source_adapters, official_source_adapter_names
from .official_source_http import (
    OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS,
    OFFICIAL_SOURCE_MAX_RESPONSE_BYTES,
    OFFICIAL_SOURCE_MAX_TIMEOUT_SECONDS,
    OFFICIAL_SOURCE_MIN_TIMEOUT_SECONDS,
)
from .official_source_operations import OfficialSourceOperationKind
from .source_registry import resolve_source

NEWS_CENTER_V1_VERSION = "1.0.0"
NEWS_CENTER_V1_OFFICIAL_SOURCES: tuple[str, ...] = (
    "KAP", "TCMB", "TÜİK", "SPK", "Hazine ve Maliye Bakanlığı",
    "Borsa İstanbul", "Resmî Gazete",
)
NEWS_CENTER_V1_CAPABILITIES: tuple[str, ...] = (
    "Manuel haber arşivi", "Güvenilir kaynak sözlüğü", "Olay gruplama ve birleştirme",
    "Deterministik etki etiketleri", "Portföy Etki Radarı", "Sektör Etki Haritası",
    "Bugünün Önemli Gelişmeleri", "Ekonomik Takvim", "KAP Akışı", "Hisse Haberleri",
    "Gün Sonu Haber ve Olay Özeti", "Son Dakika Haber Akışı", "Gelişmiş Haber Arşivi",
    "Kontrollü resmî kaynak besleme", "Resmî kaynak yapısal sağlık tanılaması",
    "Kaynak operasyon audit geçmişi", "Günlük Haber Merkezi Operasyon ekranı",
)
NEWS_CENTER_V1_GUARDRAILS: tuple[str, ...] = (
    "Resmî kaynak ağı varsayılan kapalıdır.",
    "Canlı kaynak fetch yalnız açık kullanıcı onayıyla tek URL için yapılır.",
    "Dry-run arşivlemeden önce zorunludur.",
    "Arşivleme ayrıca açık kullanıcı işlemi gerektirir.",
    "Otomatik polling yoktur.", "Toplu scraping yoktur.", "Arka plan kaynak taraması yoktur.",
    "Haber Merkezi fiyat yönü veya AL/SAT üretmez.",
    "Haber kayıtları teknik analiz skorunu doğrudan değiştirmez.",
    "Kaynak audit günlüğü haber gövdesi veya HTML yanıtı saklamaz.",
)

@dataclass(frozen=True, slots=True)
class NewsCenterV1Check:
    name: str
    passed: bool
    detail: str = ""

@dataclass(frozen=True, slots=True)
class NewsCenterV1Status:
    version: str
    checks: tuple[NewsCenterV1Check, ...]
    @property
    def passed_count(self)->int: return sum(x.passed for x in self.checks)
    @property
    def check_count(self)->int: return len(self.checks)
    @property
    def ready(self)->bool: return bool(self.checks) and self.passed_count==self.check_count
    @property
    def failures(self)->tuple[str,...]: return tuple(x.detail or x.name for x in self.checks if not x.passed)

def _check(checks,name,passed,detail):
    checks.append(NewsCenterV1Check(name=name, passed=bool(passed), detail="" if passed else detail))

def validate_news_center_v1_backend()->NewsCenterV1Status:
    """Yalnız yerel/deterministik V1 kontrolü; ağ isteği, ping, HEAD/GET veya polling yapmaz."""
    checks=[]
    _check(checks,"version_semver",bool(re.fullmatch(r"\d+\.\d+\.\d+",NEWS_CENTER_V1_VERSION)),"V1 sürüm numarası semver biçiminde değil.")
    names=official_source_adapter_names()
    _check(checks,"official_source_set",names==NEWS_CENTER_V1_OFFICIAL_SOURCES,"Aktif resmî adapter listesi V1 manifestiyle eşleşmiyor.")
    health=diagnose_official_source_adapters()
    _check(checks,"official_adapter_health",len(health)==7 and all(x.ready for x in health),"Yedi resmî adapterin tümü yapısal olarak hazır değil.")
    _check(checks,"official_adapter_49_checks",sum(x.check_count for x in health)==49 and sum(x.passed_count for x in health)==49,"Resmî adapter yapısal sağlık toplamı 49/49 değil.")
    _check(checks,"health_has_no_network_probe",all(x.network_probe_performed is False for x in health),"Yapısal sağlık tanılaması ağ testi yapıyor.")
    registry_ok=True
    for source_name in NEWS_CENTER_V1_OFFICIAL_SOURCES:
        r=resolve_source(source_name)
        if r is None or r.canonical_name!=source_name or r.tier is not SourceTier.TIER_1_OFFICIAL:
            registry_ok=False; break
    _check(checks,"tier1_registry",registry_ok,"V1 resmî kaynaklarından biri Tier-1 sözlükte doğrulanamadı.")
    _check(checks,"http_timeout_contract",OFFICIAL_SOURCE_MIN_TIMEOUT_SECONDS==1 and OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS==10 and OFFICIAL_SOURCE_MAX_TIMEOUT_SECONDS==30,"Ortak HTTP timeout sözleşmesi 1/10/30 saniye değil.")
    _check(checks,"http_size_contract",OFFICIAL_SOURCE_MAX_RESPONSE_BYTES==2_000_000,"Ortak HTTP yanıt sınırı 2 MB değil.")
    expected={"PREVIEW_BLOCKED","PREVIEW_SUCCESS","PREVIEW_ERROR","ARCHIVE_SUCCESS","ARCHIVE_DUPLICATE","ARCHIVE_ERROR"}
    _check(checks,"operation_audit_contract",{x.value for x in OfficialSourceOperationKind}==expected,"Kaynak operasyon audit olay sözleşmesi V1 manifestiyle eşleşmiyor.")
    _check(checks,"capability_manifest",len(NEWS_CENTER_V1_CAPABILITIES)>=17,"V1 yetenek manifesti beklenen kapsamı taşımıyor.")
    _check(checks,"guardrail_manifest",len(NEWS_CENTER_V1_GUARDRAILS)>=10,"V1 güvenlik sınırı manifesti eksik.")
    return NewsCenterV1Status(version=NEWS_CENTER_V1_VERSION, checks=tuple(checks))
