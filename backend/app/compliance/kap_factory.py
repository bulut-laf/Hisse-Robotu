from __future__ import annotations

from typing import Any

from backend.app.compliance.kap_settings import KapSettings
from backend.app.compliance.kap_vbts_service import KapVbtsService


def build_kap_vbts_service(
    *,
    http_get: Any,
) -> KapVbtsService:
    """Ortam ayarlarından KAP/VBTS servisini oluşturur."""

    settings = KapSettings.from_environment()
    http_source = settings.build_http_source(
        http_get=http_get,
    )

    return KapVbtsService(
        http_source=http_source,
    )
