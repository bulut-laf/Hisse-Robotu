from __future__ import annotations

from pathlib import Path


DASHBOARD_PATH = Path("backend/dashboard.py")


def source() -> str:
    return DASHBOARD_PATH.read_text(encoding="utf-8")


def test_temel_analiz_kap_api_durumunu_gosterir() -> None:
    text = source()

    assert "KAP API erişim durumu" in text
    assert "load_kap_api_configuration" in text
    assert "validate_kap_api_configuration" in text
    assert "Canlı güncelleme" in text


def test_canli_veri_cekme_devre_disi_mesaji_gorunur() -> None:
    text = source()

    assert "Canlı KAP veri çekme bu aşamada devre dışıdır." in text
    assert "Manuel CSV/JSON bilanço yükleme yolu aktiftir." in text


def test_api_anahtari_dashboardda_yazdirilmaz() -> None:
    text = source()

    assert "configuration.api_key" not in text
    assert "API anahtarı ve istemci bilgileri ekranda gösterilmez" in text
