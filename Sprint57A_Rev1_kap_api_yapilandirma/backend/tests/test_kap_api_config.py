from __future__ import annotations

from backend.app.data.kap_api_config import (
    KapApiMode,
    load_kap_api_configuration,
    validate_kap_api_configuration,
)


def test_bos_ortam_yapilandirilmadi_ve_kilitli(monkeypatch) -> None:
    for key in (
        "HISSE_ROBOTU_KAP_API_MODE",
        "HISSE_ROBOTU_KAP_API_BASE_URL",
        "HISSE_ROBOTU_KAP_API_CLIENT_ID",
        "HISSE_ROBOTU_KAP_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    configuration = load_kap_api_configuration()
    status = validate_kap_api_configuration(configuration)

    assert configuration.mode is KapApiMode.UNCONFIGURED
    assert status.locked is True
    assert "manuel CSV/JSON" in status.explanation


def test_test_modu_gecerli_https_bilgileriyle_dogrulanir(
    monkeypatch,
) -> None:
    monkeypatch.setenv("HISSE_ROBOTU_KAP_API_MODE", "test")
    monkeypatch.setenv(
        "HISSE_ROBOTU_KAP_API_BASE_URL",
        "https://api.example.test",
    )
    monkeypatch.setenv(
        "HISSE_ROBOTU_KAP_API_CLIENT_ID",
        "client-1234",
    )
    monkeypatch.setenv(
        "HISSE_ROBOTU_KAP_API_KEY",
        "secret-value",
    )

    configuration = load_kap_api_configuration()
    status = validate_kap_api_configuration(configuration)

    assert configuration.mode is KapApiMode.TEST
    assert status.locked is False
    assert configuration.masked_client_id == "cl****34"


def test_http_api_adresi_reddedilir(monkeypatch) -> None:
    monkeypatch.setenv("HISSE_ROBOTU_KAP_API_MODE", "production")
    monkeypatch.setenv(
        "HISSE_ROBOTU_KAP_API_BASE_URL",
        "http://api.example.test",
    )
    monkeypatch.setenv(
        "HISSE_ROBOTU_KAP_API_CLIENT_ID",
        "client",
    )
    monkeypatch.setenv(
        "HISSE_ROBOTU_KAP_API_KEY",
        "secret",
    )

    status = validate_kap_api_configuration(
        load_kap_api_configuration()
    )

    assert status.locked is True
    assert "HTTPS" in status.explanation


def test_api_anahtari_durum_nesnesinde_maskelenmez_ama_arayuzde_gosterilmez(
    monkeypatch,
) -> None:
    monkeypatch.setenv("HISSE_ROBOTU_KAP_API_KEY", "very-secret-key")

    configuration = load_kap_api_configuration()

    assert configuration.api_key == "very-secret-key"
    assert "very-secret-key" not in configuration.masked_client_id
