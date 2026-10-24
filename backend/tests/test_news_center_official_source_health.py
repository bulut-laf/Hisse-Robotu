from dataclasses import replace

import pytest

from backend.app.news_center.models import SourceTier
from backend.app.news_center.official_source_health import (
    OFFICIAL_SOURCE_ADAPTER_SPECS,
    OfficialSourceAdapterSpec,
    diagnose_official_source_adapters,
    official_source_adapter_names,
)
from backend.app.news_center.official_source_http import (
    OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS,
)
from backend.app.news_center.source_registry import resolve_source


EXPECTED_NAMES = (
    "KAP",
    "TCMB",
    "TÜİK",
    "SPK",
    "Hazine ve Maliye Bakanlığı",
    "Borsa İstanbul",
    "Resmî Gazete",
)


def test_yedi_resmi_adapter_speci_var():
    assert len(OFFICIAL_SOURCE_ADAPTER_SPECS) == 7


def test_adapter_isimleri_merkezi_kayittan_gelir():
    assert official_source_adapter_names() == EXPECTED_NAMES


@pytest.mark.parametrize("spec", OFFICIAL_SOURCE_ADAPTER_SPECS)
def test_her_ornek_url_kaynak_validatorunden_gecer(spec):
    assert spec.validator(spec.sample_url) is not None


@pytest.mark.parametrize("spec", OFFICIAL_SOURCE_ADAPTER_SPECS)
def test_her_kaynak_adi_tier1_cozumlenir(spec):
    resolved = resolve_source(spec.canonical_name)
    assert resolved is not None
    assert resolved.canonical_name == spec.canonical_name
    assert resolved.tier is SourceTier.TIER_1_OFFICIAL


@pytest.mark.parametrize("spec", OFFICIAL_SOURCE_ADAPTER_SPECS)
def test_her_ornek_domain_tier1_cozumlenir(spec):
    resolved = resolve_source("", spec.sample_url)
    assert resolved is not None
    assert resolved.canonical_name == spec.canonical_name
    assert resolved.tier is SourceTier.TIER_1_OFFICIAL


@pytest.mark.parametrize("spec", OFFICIAL_SOURCE_ADAPTER_SPECS)
def test_her_adapter_ag_varsayilan_kapali(spec):
    adapter = spec.adapter_type(fetcher=lambda *_: (_ for _ in ()).throw(
        AssertionError("fetcher çağrılmamalı")
    ))
    assert adapter.network_enabled is False


@pytest.mark.parametrize("spec", OFFICIAL_SOURCE_ADAPTER_SPECS)
def test_her_adapter_ortak_timeout_kullanir(spec):
    adapter = spec.adapter_type(fetcher=lambda *_: (_ for _ in ()).throw(
        AssertionError("fetcher çağrılmamalı")
    ))
    assert adapter.timeout_seconds == OFFICIAL_SOURCE_DEFAULT_TIMEOUT_SECONDS


@pytest.mark.parametrize("spec", OFFICIAL_SOURCE_ADAPTER_SPECS)
def test_default_ag_kilidi_fetcheri_cagirmaz(spec):
    calls = []

    def forbidden_fetcher(url, timeout):
        calls.append((url, timeout))
        raise AssertionError("fetcher çağrılmamalı")

    adapter = spec.adapter_type(fetcher=forbidden_fetcher)

    with pytest.raises(spec.error_type, match="ağ erişimi kapalı"):
        adapter.fetch(spec.sample_url)

    assert calls == []


def test_tum_yapisal_tanilamalar_hazir():
    statuses = diagnose_official_source_adapters()
    assert len(statuses) == 7
    assert all(status.ready for status in statuses)


def test_toplam_kontrol_sayisi_49():
    statuses = diagnose_official_source_adapters()
    assert sum(status.check_count for status in statuses) == 49
    assert sum(status.passed_count for status in statuses) == 49


def test_tanilama_canli_ag_testi_yapmaz():
    statuses = diagnose_official_source_adapters()
    assert all(status.network_probe_performed is False for status in statuses)


def test_hazir_status_issue_uretmez():
    statuses = diagnose_official_source_adapters()
    assert all(status.issues == () for status in statuses)


def test_adapter_sinif_adi_statusa_yansir():
    statuses = diagnose_official_source_adapters()
    assert statuses[0].adapter_name == "KapUrlAdapter"
    assert statuses[-1].adapter_name == "ResmiGazeteArticleUrlAdapter"


def test_bozuk_validator_hata_statusu_uretir():
    original = OFFICIAL_SOURCE_ADAPTER_SPECS[0]

    def broken_validator(url):
        raise ValueError("bilerek bozuk validator")

    broken = replace(original, validator=broken_validator)
    status = diagnose_official_source_adapters((broken,))[0]

    assert status.ready is False
    assert status.check_count == 7
    assert status.passed_count == 6
    assert any("URL sözleşmesi" in issue for issue in status.issues)


def test_guvenilir_olmayan_kanonik_ad_hata_statusu_uretir():
    original = OFFICIAL_SOURCE_ADAPTER_SPECS[0]
    broken = replace(original, canonical_name="KAP-BOZUK")
    status = diagnose_official_source_adapters((broken,))[0]

    assert status.ready is False
    assert status.passed_count == 5
    assert len(status.issues) == 2


def test_spec_tuple_degisken_adapter_sayisini_ui_icin_tek_kaynaktan_verir():
    assert len(official_source_adapter_names()) == len(OFFICIAL_SOURCE_ADAPTER_SPECS)
