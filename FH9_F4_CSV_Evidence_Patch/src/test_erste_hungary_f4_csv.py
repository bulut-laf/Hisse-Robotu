from datetime import date
from decimal import Decimal

from backend.app.funds.international.erste_hungary_f4_csv import (
    parse_bamosz_csv, fund_size_change, net_flow_ratio
)

def test_metadata_before_header_and_iso_8859_2():
    body = (
        '"Letöltés időpontja";"2026.10.24. 08:00"\n'
        '"Alap neve:";"Erste Felelős Részvény"\n'
        '"Dátum";"Árfolyam";"NEÉ";"Kifizetett hozam";"Napi befjegy. forgalom"\n'
        '"2026.10.22.";"1.234,56";"100.000,00";"";"500,00"\n'
        '"2026.10.23.";"1.240,00";"105.000,00";"";"600,00"\n'
    ).encode("iso-8859-2")
    parsed = parse_bamosz_csv(body, "AT0000627476")
    assert parsed.encoding == "iso-8859-2"
    assert parsed.fund_name == "Erste Felelős Részvény"
    assert len(parsed.rows) == 2
    assert parsed.rows[-1].nav == Decimal("105000.00")
    assert parsed.rows[-1].turnover == Decimal("600.00")

def test_fund_size_change_uses_latest_two_valid_nav_rows():
    body = (
        '"Dátum";"Árfolyam";"NEÉ"\n'
        '"2026.10.22.";"1,0";"100,0"\n'
        '"2026.10.23.";"1,0";"105,0"\n'
    ).encode("iso-8859-2")
    parsed = parse_bamosz_csv(body, "AT0000627476")
    assert fund_size_change(parsed.rows) == Decimal("0.05")

def test_no_net_flow_proxy_from_daily_turnover():
    assert net_flow_ratio(official_net_investor_flow=None,
                          prior_fund_nav=Decimal("100")) is None
    assert net_flow_ratio(official_net_investor_flow=Decimal("2"),
                          prior_fund_nav=Decimal("100")) == Decimal("0.02")

def test_missing_header_fails_closed():
    try:
        parse_bamosz_csv(b'"Letoltes";"valami"\n"meta";"adat"\n', "AT0000627476")
    except ValueError as exc:
        assert "CSV_DAILY_HEADER_NOT_FOUND" in str(exc)
    else:
        raise AssertionError("expected explicit header error")
