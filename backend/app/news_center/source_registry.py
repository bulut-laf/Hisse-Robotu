from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlparse

from .models import SourceTier


@dataclass(frozen=True, slots=True)
class TrustedSource:
    canonical_name: str
    tier: SourceTier
    aliases: tuple[str, ...]
    domains: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceResolution:
    canonical_name: str
    tier: SourceTier
    matched_by: str
    matched_value: str


TRUSTED_SOURCES: tuple[TrustedSource, ...] = (
    TrustedSource(
        canonical_name="TCMB",
        tier=SourceTier.TIER_1_OFFICIAL,
        aliases=(
            "tcmb",
            "türkiye cumhuriyet merkez bankası",
            "turkiye cumhuriyet merkez bankasi",
        ),
        domains=("tcmb.gov.tr",),
    ),
    TrustedSource(
        canonical_name="TÜİK",
        tier=SourceTier.TIER_1_OFFICIAL,
        aliases=(
            "tüik",
            "tuik",
            "türkiye istatistik kurumu",
            "turkiye istatistik kurumu",
        ),
        domains=("tuik.gov.tr", "data.tuik.gov.tr"),
    ),
    TrustedSource(
        canonical_name="KAP",
        tier=SourceTier.TIER_1_OFFICIAL,
        aliases=(
            "kap",
            "kamuyu aydınlatma platformu",
            "kamuyu aydinlatma platformu",
        ),
        domains=("kap.org.tr",),
    ),
    TrustedSource(
        canonical_name="Borsa İstanbul",
        tier=SourceTier.TIER_1_OFFICIAL,
        aliases=(
            "borsa istanbul",
            "borsa i̇stanbul",
            "bist",
        ),
        domains=("borsaistanbul.com",),
    ),
    TrustedSource(
        canonical_name="SPK",
        tier=SourceTier.TIER_1_OFFICIAL,
        aliases=(
            "spk",
            "sermaye piyasası kurulu",
            "sermaye piyasasi kurulu",
        ),
        domains=("spk.gov.tr",),
    ),
    TrustedSource(
        canonical_name="Hazine ve Maliye Bakanlığı",
        tier=SourceTier.TIER_1_OFFICIAL,
        aliases=(
            "hazine ve maliye bakanlığı",
            "hazine ve maliye bakanligi",
            "hmb",
        ),
        domains=("hmb.gov.tr",),
    ),
    TrustedSource(
        canonical_name="Resmî Gazete",
        tier=SourceTier.TIER_1_OFFICIAL,
        aliases=(
            "resmî gazete",
            "resmi gazete",
        ),
        domains=("resmigazete.gov.tr",),
    ),
    TrustedSource(
        canonical_name="Şirket Yatırımcı İlişkileri",
        tier=SourceTier.TIER_1_OFFICIAL,
        aliases=(
            "şirket yatırımcı ilişkileri",
            "sirket yatirimci iliskileri",
            "yatırımcı ilişkileri",
            "yatirimci iliskileri",
        ),
    ),
    TrustedSource(
        canonical_name="Anadolu Ajansı",
        tier=SourceTier.OTHER_VERIFIED,
        aliases=(
            "anadolu ajansı",
            "anadolu ajansi",
            "aa",
        ),
        domains=("aa.com.tr",),
    ),
    TrustedSource(
        canonical_name="TRT Haber",
        tier=SourceTier.OTHER_VERIFIED,
        aliases=(
            "trt haber",
            "trthaber",
        ),
        domains=("trthaber.com",),
    ),
    TrustedSource(
        canonical_name="Reuters",
        tier=SourceTier.TIER_2_MAJOR_FINANCIAL,
        aliases=("reuters",),
        domains=("reuters.com",),
    ),
    TrustedSource(
        canonical_name="Bloomberg",
        tier=SourceTier.TIER_2_MAJOR_FINANCIAL,
        aliases=("bloomberg",),
        domains=("bloomberg.com",),
    ),
)


def _normalize_name(value: str) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    return normalized.replace("i̇", "i")


def _extract_host(reference: str) -> str:
    raw = str(reference or "").strip()
    if not raw:
        return ""
    candidate = raw if "://" in raw else f"https://{raw}"
    try:
        host = (urlparse(candidate).hostname or "").lower().strip(".")
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def resolve_source(
    source_name: str,
    source_reference: str = "",
) -> SourceResolution | None:
    """Kaynağı yalnız beyaz listedeki açık eşleşmelerle çözümler."""

    normalized_name = _normalize_name(source_name)
    if normalized_name:
        for source in TRUSTED_SOURCES:
            aliases = {_normalize_name(alias) for alias in source.aliases}
            if normalized_name in aliases:
                return SourceResolution(
                    canonical_name=source.canonical_name,
                    tier=source.tier,
                    matched_by="source_name",
                    matched_value=str(source_name).strip(),
                )

    host = _extract_host(source_reference)
    if host:
        for source in TRUSTED_SOURCES:
            for domain in source.domains:
                normalized_domain = domain.lower().strip(".")
                if host == normalized_domain or host.endswith(f".{normalized_domain}"):
                    return SourceResolution(
                        canonical_name=source.canonical_name,
                        tier=source.tier,
                        matched_by="domain",
                        matched_value=host,
                    )
    return None
