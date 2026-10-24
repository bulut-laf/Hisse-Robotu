from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class KapApiMode(str, Enum):
    UNCONFIGURED = "Yapılandırılmadı"
    TEST = "Test"
    PRODUCTION = "Üretim"


@dataclass(frozen=True)
class KapApiConfiguration:
    mode: KapApiMode
    base_url: str
    client_id: str
    api_key: str
    timeout_seconds: int = 30

    @property
    def configured(self) -> bool:
        return (
            self.mode is not KapApiMode.UNCONFIGURED
            and bool(self.base_url)
            and bool(self.client_id)
            and bool(self.api_key)
        )

    @property
    def masked_client_id(self) -> str:
        if not self.client_id:
            return "Tanımlı değil"
        if len(self.client_id) <= 4:
            return "****"
        return self.client_id[:2] + "****" + self.client_id[-2:]


@dataclass(frozen=True)
class KapApiConfigurationStatus:
    configuration: KapApiConfiguration
    locked: bool
    explanation: str
    missing_fields: tuple[str, ...]


def _mode_from_environment(value: str) -> KapApiMode:
    normalized = value.strip().lower()

    if normalized in {"test", "sandbox"}:
        return KapApiMode.TEST
    if normalized in {"production", "prod", "üretim", "uretim"}:
        return KapApiMode.PRODUCTION
    return KapApiMode.UNCONFIGURED


def load_kap_api_configuration() -> KapApiConfiguration:
    timeout_raw = os.getenv("HISSE_ROBOTU_KAP_API_TIMEOUT", "30").strip()

    try:
        timeout = int(timeout_raw)
    except ValueError:
        timeout = 30

    timeout = min(max(timeout, 5), 120)

    return KapApiConfiguration(
        mode=_mode_from_environment(
            os.getenv("HISSE_ROBOTU_KAP_API_MODE", "")
        ),
        base_url=os.getenv(
            "HISSE_ROBOTU_KAP_API_BASE_URL",
            "",
        ).strip(),
        client_id=os.getenv(
            "HISSE_ROBOTU_KAP_API_CLIENT_ID",
            "",
        ).strip(),
        api_key=os.getenv(
            "HISSE_ROBOTU_KAP_API_KEY",
            "",
        ).strip(),
        timeout_seconds=timeout,
    )


def validate_kap_api_configuration(
    configuration: KapApiConfiguration,
) -> KapApiConfigurationStatus:
    missing: list[str] = []

    if configuration.mode is KapApiMode.UNCONFIGURED:
        missing.append("erişim modu")
    if not configuration.base_url:
        missing.append("API adresi")
    if not configuration.client_id:
        missing.append("istemci kimliği")
    if not configuration.api_key:
        missing.append("API anahtarı")

    if configuration.base_url:
        parsed = urlparse(configuration.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            return KapApiConfigurationStatus(
                configuration=configuration,
                locked=True,
                explanation=(
                    "KAP API adresi geçerli bir HTTPS adresi olmalıdır."
                ),
                missing_fields=tuple(missing),
            )

    if missing:
        return KapApiConfigurationStatus(
            configuration=configuration,
            locked=True,
            explanation=(
                "KAP API bağlantısı yapılandırılmadı. "
                "Canlı finansal veri güncellemesi kilitli; "
                "manuel CSV/JSON yolu kullanılabilir."
            ),
            missing_fields=tuple(missing),
        )

    return KapApiConfigurationStatus(
        configuration=configuration,
        locked=False,
        explanation=(
            f"KAP API yapılandırması {configuration.mode.value} "
            "modunda doğrulandı. Bu sprint bağlantı bilgilerini "
            "yalnızca kontrol eder; canlı veri çekmez."
        ),
        missing_fields=(),
    )
