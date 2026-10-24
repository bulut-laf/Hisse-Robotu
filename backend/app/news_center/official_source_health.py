from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .borsa_istanbul_adapter import (
    BorsaIstanbulAdapterError,
    BorsaIstanbulAnnouncementUrlAdapter,
    validate_borsa_istanbul_announcement_url,
)
from .hmb_adapter import (
    HmbAdapterError,
    HmbPressUrlAdapter,
    validate_hmb_press_url,
)
from .kap_adapter import (
    KapAdapterError,
    KapUrlAdapter,
    validate_kap_detail_url,
)
from .models import SourceTier
from .official_source_http import OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS
from .resmi_gazete_adapter import (
    ResmiGazeteAdapterError,
    ResmiGazeteArticleUrlAdapter,
    validate_resmi_gazete_article_url,
)
from .source_registry import resolve_source
from .spk_adapter import (
    SpkAdapterError,
    SpkPressUrlAdapter,
    validate_spk_press_url,
)
from .tcmb_adapter import (
    TcmbAdapterError,
    TcmbPressUrlAdapter,
    validate_tcmb_press_url,
)
from .tuik_adapter import (
    TuikAdapterError,
    TuikPressUrlAdapter,
    validate_tuik_press_url,
)


Validator = Callable[[str], object]


@dataclass(frozen=True, slots=True)
class OfficialSourceAdapterSpec:
    canonical_name: str
    adapter_type: type
    validator: Validator
    error_type: type[RuntimeError]
    sample_url: str


@dataclass(frozen=True, slots=True)
class OfficialSourceHealthCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class OfficialSourceHealthStatus:
    canonical_name: str
    adapter_name: str
    checks: tuple[OfficialSourceHealthCheck, ...]
    network_probe_performed: bool = False

    @property
    def passed_count(self) -> int:
        return sum(check.passed for check in self.checks)

    @property
    def check_count(self) -> int:
        return len(self.checks)

    @property
    def ready(self) -> bool:
        return bool(self.checks) and self.passed_count == self.check_count

    @property
    def issues(self) -> tuple[str, ...]:
        return tuple(
            check.detail or check.name
            for check in self.checks
            if not check.passed
        )


OFFICIAL_SOURCE_ADAPTER_SPECS: tuple[OfficialSourceAdapterSpec, ...] = (
    OfficialSourceAdapterSpec(
        canonical_name="KAP",
        adapter_type=KapUrlAdapter,
        validator=validate_kap_detail_url,
        error_type=KapAdapterError,
        sample_url="https://www.kap.org.tr/tr/Bildirim/1",
    ),
    OfficialSourceAdapterSpec(
        canonical_name="TCMB",
        adapter_type=TcmbPressUrlAdapter,
        validator=validate_tcmb_press_url,
        error_type=TcmbAdapterError,
        sample_url=(
            "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/"
            "Main+Menu/Duyurular/Basin/2026/DUY2026-01"
        ),
    ),
    OfficialSourceAdapterSpec(
        canonical_name="TÜİK",
        adapter_type=TuikPressUrlAdapter,
        validator=validate_tuik_press_url,
        error_type=TuikAdapterError,
        sample_url="https://veriportali.tuik.gov.tr/tr/press/1",
    ),
    OfficialSourceAdapterSpec(
        canonical_name="SPK",
        adapter_type=SpkPressUrlAdapter,
        validator=validate_spk_press_url,
        error_type=SpkAdapterError,
        sample_url=(
            "https://spk.gov.tr/duyurular/basin-duyurulari/2026/"
            "ornek-duyuru"
        ),
    ),
    OfficialSourceAdapterSpec(
        canonical_name="Hazine ve Maliye Bakanlığı",
        adapter_type=HmbPressUrlAdapter,
        validator=validate_hmb_press_url,
        error_type=HmbAdapterError,
        sample_url="https://www.hmb.gov.tr/duyuru/ornek-duyuru",
    ),
    OfficialSourceAdapterSpec(
        canonical_name="Borsa İstanbul",
        adapter_type=BorsaIstanbulAnnouncementUrlAdapter,
        validator=validate_borsa_istanbul_announcement_url,
        error_type=BorsaIstanbulAdapterError,
        sample_url="https://www.borsaistanbul.com/duyuru/1/ornek-duyuru",
    ),
    OfficialSourceAdapterSpec(
        canonical_name="Resmî Gazete",
        adapter_type=ResmiGazeteArticleUrlAdapter,
        validator=validate_resmi_gazete_article_url,
        error_type=ResmiGazeteAdapterError,
        sample_url=(
            "https://www.resmigazete.gov.tr/eskiler/2026/01/"
            "20260101-1.htm"
        ),
    ),
)


def official_source_adapter_names() -> tuple[str, ...]:
    return tuple(spec.canonical_name for spec in OFFICIAL_SOURCE_ADAPTER_SPECS)


def _check(
    checks: list[OfficialSourceHealthCheck],
    name: str,
    passed: bool,
    detail: str,
) -> None:
    checks.append(
        OfficialSourceHealthCheck(
            name=name,
            passed=bool(passed),
            detail="" if passed else detail,
        )
    )


def _diagnose_spec(spec: OfficialSourceAdapterSpec) -> OfficialSourceHealthStatus:
    checks: list[OfficialSourceHealthCheck] = []

    resolution_by_name = resolve_source(spec.canonical_name)
    _check(
        checks,
        "trusted_source_name",
        (
            resolution_by_name is not None
            and resolution_by_name.canonical_name == spec.canonical_name
            and resolution_by_name.tier is SourceTier.TIER_1_OFFICIAL
        ),
        "Kaynak adı güvenilir Tier-1 kaynak sözlüğünde doğrulanamadı.",
    )

    resolution_by_domain = resolve_source("", spec.sample_url)
    _check(
        checks,
        "trusted_source_domain",
        (
            resolution_by_domain is not None
            and resolution_by_domain.canonical_name == spec.canonical_name
            and resolution_by_domain.tier is SourceTier.TIER_1_OFFICIAL
        ),
        "Örnek resmî alan adı güvenilir kaynak sözlüğüyle eşleşmedi.",
    )

    try:
        spec.validator(spec.sample_url)
    except Exception as exc:  # adapter validator sözleşmesi tanılama için izole edilir.
        _check(
            checks,
            "url_contract",
            False,
            f"Adapter URL sözleşmesi başarısız: {exc}",
        )
    else:
        _check(
            checks,
            "url_contract",
            True,
            "",
        )

    fetch_calls: list[tuple[str, int]] = []

    def forbidden_fetcher(url: str, timeout_seconds: int):
        fetch_calls.append((url, timeout_seconds))
        raise AssertionError("Yapısal tanılama sırasında ağ/fetcher çağrılmamalıdır.")

    adapter = None
    try:
        adapter = spec.adapter_type(fetcher=forbidden_fetcher)
    except Exception as exc:
        _check(
            checks,
            "adapter_construct",
            False,
            f"Adapter varsayılan ayarlarla oluşturulamadı: {exc}",
        )
    else:
        _check(checks, "adapter_construct", True, "")

    _check(
        checks,
        "network_default_off",
        adapter is not None and getattr(adapter, "network_enabled", None) is False,
        "Adapter ağ erişimi varsayılan kapalı değil.",
    )

    _check(
        checks,
        "default_timeout",
        (
            adapter is not None
            and getattr(adapter, "timeout_seconds", None)
            == OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS
        ),
        "Adapter ortak varsayılan timeout değerini kullanmıyor.",
    )

    network_guard_ok = False
    if adapter is not None:
        try:
            adapter.fetch(spec.sample_url)
        except spec.error_type as exc:
            network_guard_ok = (
                "ağ erişimi kapalı" in str(exc).casefold()
                and not fetch_calls
            )
        except Exception:
            network_guard_ok = False

    _check(
        checks,
        "network_guard",
        network_guard_ok,
        "Varsayılan ağ kilidi fetcher çağrısından önce isteği durdurmadı.",
    )

    return OfficialSourceHealthStatus(
        canonical_name=spec.canonical_name,
        adapter_name=spec.adapter_type.__name__,
        checks=tuple(checks),
        network_probe_performed=False,
    )


def diagnose_official_source_adapters(
    specs: tuple[OfficialSourceAdapterSpec, ...] = OFFICIAL_SOURCE_ADAPTER_SPECS,
) -> tuple[OfficialSourceHealthStatus, ...]:
    """
    Yedi kontrollü resmî adapterin yalnız yapısal/offline sağlık kontrolünü yapar.

    İnternete ping atmaz ve canlı kaynak kullanılabilirliği iddiasında bulunmaz.
    Kontroller güvenilir kaynak kaydı, URL sözleşmesi, varsayılan ağ kilidi ve
    ortak timeout sözleşmesiyle sınırlıdır.
    """
    return tuple(_diagnose_spec(spec) for spec in specs)
