from datetime import date, datetime, timezone

import pytest

from backend.app.funds.kap_portfolio_auto_ingestion import (
    KAP_DISCLOSURES_URL,
    auto_ingest_kap_portfolio_reports,
    discover_kap_portfolio_reports,
    parse_kap_disclosures_for_portfolio_reports,
)
from backend.app.funds.kap_portfolio_ingestion import (
    KapFundPortfolioError,
    KapPortfolioIngestionResult,
    KapPortfolioReportReference,
)
from backend.app.funds.contracts import DataQualityState
from backend.app.funds.portfolio_tracking import (
    FundPortfolioSnapshot,
    FundPortfolioSnapshotJsonStore,
    PortfolioSnapshotStoreResult,
)


def test_discovery_parser_filters_portfolio_reports_and_known_fund_codes():
    payload = [
        {
            "basic": {
                "disclosureIndex": 1646130,
                "title": "Portföy Dağılım Raporu",
                "fundName": "ATLAS PORTFÖY BEŞİNCİ HİSSE SENEDİ SERBEST FON AP5",
                "summary": "AP5 FON - TEMMUZ 2026 PORTFÖY DAĞILIM RAPORU",
            }
        },
        {
            "basic": {
                "disclosureIndex": 1646000,
                "title": "Portföy Dağılım Raporu",
                "fundName": "BAŞKA FON XYZ",
            }
        },
        {
            "basic": {
                "disclosureIndex": 1645000,
                "title": "Yönetim Kurulu Kararı",
                "fundName": "AP5",
            }
        },
    ]

    candidates = parse_kap_disclosures_for_portfolio_reports(
        payload,
        fund_codes=("AP5",),
    )

    assert len(candidates) == 1
    assert candidates[0].notification_id == "1646130"
    assert candidates[0].detail_url == "https://www.kap.org.tr/tr/Bildirim/1646130"


def test_discovery_requires_explicit_network_enablement():
    calls = []

    def forbidden_fetcher(url, timeout):
        calls.append((url, timeout))
        raise AssertionError("NETWORK_CALLED")

    with pytest.raises(KapFundPortfolioError, match="DISCOVERY_NETWORK_DISABLED"):
        discover_kap_portfolio_reports(
            fund_codes=("AP5",),
            fetcher=forbidden_fetcher,
        )

    assert calls == []


def test_discovery_fetches_official_json_once_and_is_bounded():
    payload = b'''[
      {"disclosureIndex":1646130,"title":"Portf\\u00f6y Da\\u011f\\u0131l\\u0131m Raporu","fundName":"AP5"}
    ]'''
    calls = []

    def fetcher(url, timeout):
        calls.append((url, timeout))
        return payload, KAP_DISCLOSURES_URL, "application/json; charset=utf-8"

    result = discover_kap_portfolio_reports(
        fund_codes=("AP5",),
        network_enabled=True,
        fetcher=fetcher,
    )

    assert calls == [(KAP_DISCLOSURES_URL, 10)]
    assert [item.notification_id for item in result] == ["1646130"]


def test_auto_ingestion_isolates_candidate_failures(monkeypatch, tmp_path):
    store = FundPortfolioSnapshotJsonStore(tmp_path / "portfolio_snapshots.json")
    payload = b'''[
      {"disclosureIndex":1646130,"title":"Portf\\u00f6y Da\\u011f\\u0131l\\u0131m Raporu","fundName":"AP5"},
      {"disclosureIndex":1628517,"title":"Portf\\u00f6y Da\\u011f\\u0131l\\u0131m Raporu","fundName":"AP5"}
    ]'''

    def discovery_fetcher(url, timeout):
        return payload, KAP_DISCLOSURES_URL, "application/json"

    def fake_ingest(detail_url, **_kwargs):
        if detail_url.endswith("1646130"):
            raise KapFundPortfolioError("KAP_HTTP_ERROR:403")
        reference = KapPortfolioReportReference(
            notification_id="1628517",
            detail_url=detail_url,
            attachment_url="https://www.kap.org.tr/tr/api/file/download/abc",
            attachment_name="AP5.pdf",
            publication_at=datetime(2026, 7, 8, tzinfo=timezone.utc),
            report_year=2026,
            report_month=6,
        )
        snapshot = FundPortfolioSnapshot(
            canonical_fund_id="fund:tefas:AP5",
            portfolio_date=date(2026, 6, 30),
            publication_date=date(2026, 7, 8),
            ingested_at=datetime(2026, 9, 4, tzinfo=timezone.utc),
            provider="KAP",
            positions=(),
            data_quality_state=DataQualityState.VALID,
        )
        return KapPortfolioIngestionResult(
            reference=reference,
            snapshot=snapshot,
            store_result=PortfolioSnapshotStoreResult(
                inserted=1,
                unchanged=0,
                total_records=1,
            ),
        )

    monkeypatch.setattr(
        "backend.app.funds.kap_portfolio_auto_ingestion.ingest_kap_portfolio_report_url",
        fake_ingest,
    )

    summary = auto_ingest_kap_portfolio_reports(
        store=store,
        fund_codes=("AP5",),
        network_enabled=True,
        discovery_fetcher=discovery_fetcher,
    )

    assert summary.discovered == 2
    assert summary.attempted == 2
    assert summary.inserted == 1
    assert summary.unchanged == 0
    assert len(summary.failures) == 1
    assert summary.failures[0].notification_id == "1646130"
