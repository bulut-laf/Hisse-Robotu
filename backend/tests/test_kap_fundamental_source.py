from __future__ import annotations

from datetime import date

from backend.app.data.kap_fundamental_source import (
    KapFundamentalClient,
    normalize_kap_record,
)


def valid_record(**overrides):
    record = {
        "stockCode": "THYAO",
        "reportDate": "2026-06-30",
        "year": 2026,
        "quarter": 2,
        "currencyCode": "TRY",
        "sales": 1000,
        "grossProfit": 300,
        "operatingIncome": 180,
        "EBITDA": 220,
        "netProfit": 120,
        "totalAssets": 2500,
        "equity": 1000,
        "totalDebt": 700,
        "cash": 200,
        "currentAssets": 900,
        "currentLiabilities": 600,
        "cashFlowFromOperations": 160,
        "capex": 40,
        "sharesOutstanding": 100,
        "disclosureDate": "2026-07-20",
    }
    record.update(overrides)
    return record


def test_kap_alanlari_standart_modele_normalize_edilir():
    result = normalize_kap_record(
        valid_record(),
        requested_symbol="THYAO",
    )

    assert result["symbol"] == "THYAO"
    assert result["period_end"] == "2026-06-30"
    assert result["revenue"] == 1000
    assert result["ebitda"] == 220
    assert result["published_at"] == "2026-07-20"


def test_ceyrek_donem_tarihinden_cikarilir():
    record = valid_record()
    del record["quarter"]

    result = normalize_kap_record(
        record,
        requested_symbol="THYAO",
    )

    assert result["fiscal_quarter"] == 2


def test_client_gecerli_kayitlari_paketler():
    client = KapFundamentalClient(
        fetcher=lambda symbol, start, end: [
            valid_record(),
        ]
    )

    package = client.fetch("THYAO")

    assert len(package.periods) == 1
    assert package.status.locked is False
    assert package.status.accepted_count == 1
    assert package.status.data_identity


def test_hatalı_kayit_reddedilir_ve_kilitlenir():
    client = KapFundamentalClient(
        fetcher=lambda symbol, start, end: [
            {"stockCode": "THYAO"},
        ]
    )

    package = client.fetch("THYAO")

    assert package.periods == ()
    assert package.status.locked is True
    assert package.status.rejected_count == 1


def test_farkli_sembol_kaydi_kabul_edilmez():
    client = KapFundamentalClient(
        fetcher=lambda symbol, start, end: [
            valid_record(stockCode="ASELS"),
        ]
    )

    package = client.fetch("THYAO")

    assert package.status.locked is True
    assert "eşleşmiyor" in package.rejected_records[0]
