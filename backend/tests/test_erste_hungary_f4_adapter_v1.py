from datetime import date
from decimal import Decimal

from backend.app.funds.evidence_mapper import EvidenceState
from backend.app.funds.international.erste_hungary_f4_adapter import (
    ErsteF4Observation,
    derive_erste_f4,
)


ISIN = "AT0000627476"
D1 = date(2026, 10, 20)
D2 = date(2026, 10, 21)
AS_OF = date(2026, 10, 22)


def row(day, nav):
    return ErsteF4Observation(ISIN, day, Decimal(nav))


def test_missing_official_flow_stays_unavailable():
    result = derive_erste_f4(
        isin=ISIN,
        observations=(row(D1, "100"), row(D2, "105")),
        as_of_date=AS_OF,
        max_age_days=3,
    )
    assert result.state is EvidenceState.UNAVAILABLE
    assert result.net_flow_ratio is None
    assert result.reason == "OFFICIAL_NET_FLOW_UNAVAILABLE"


def test_stale_data_is_rejected():
    result = derive_erste_f4(
        isin=ISIN,
        observations=(row(date(2020, 1, 1), "100"),
                      row(date(2020, 1, 2), "105")),
        as_of_date=AS_OF,
        max_age_days=3,
    )
    assert result.state is EvidenceState.UNAVAILABLE
    assert result.reason == "STALE_OBSERVATION"


def test_future_observation_is_rejected():
    result = derive_erste_f4(
        isin=ISIN,
        observations=(row(D1, "100"), row(date(2026, 10, 23), "105")),
        as_of_date=AS_OF,
        max_age_days=3,
    )
    assert result.state is EvidenceState.UNAVAILABLE
    assert result.reason == "FUTURE_OBSERVATION"


def test_mismatched_isin_is_rejected():
    result = derive_erste_f4(
        isin=ISIN,
        observations=(
            row(D1, "100"),
            ErsteF4Observation("AT0000A00GA2", D2, Decimal("105")),
        ),
        as_of_date=AS_OF,
        max_age_days=3,
    )
    assert result.state is EvidenceState.UNAVAILABLE
    assert result.reason == "ISIN_MISMATCH"


def test_invalid_nav_is_rejected():
    result = derive_erste_f4(
        isin=ISIN,
        observations=(row(D1, "100"), row(D2, "0")),
        as_of_date=AS_OF,
        max_age_days=3,
    )
    assert result.state is EvidenceState.UNAVAILABLE
    assert result.reason == "INVALID_UNIT_PRICE"


def test_valid_nav_pair_does_not_prove_fund_flow():
    result = derive_erste_f4(
        isin=ISIN,
        observations=(row(D1, "100"), row(D2, "105")),
        as_of_date=AS_OF,
        max_age_days=3,
    )
    assert result.fund_size_change is None
    assert result.net_flow_ratio is None
    assert result.state is EvidenceState.UNAVAILABLE


def test_explicit_fund_size_change_is_calculated():
    result = derive_erste_f4(
        isin=ISIN,
        observations=(
            ErsteF4Observation(ISIN, D1, Decimal("100"), Decimal("1000")),
            ErsteF4Observation(ISIN, D2, Decimal("105"), Decimal("1100")),
        ),
        as_of_date=AS_OF,
        max_age_days=3,
        official_net_flow=Decimal("50"),
        prior_fund_nav=Decimal("1000"),
    )
    assert result.fund_size_change == Decimal("0.1")
    assert result.net_flow_ratio == Decimal("0.05")
    assert result.state is EvidenceState.POSITIVE


def test_fund_size_change_requires_explicit_fund_size_values():
    result = derive_erste_f4(
        isin=ISIN,
        observations=(row(D1, "100"), row(D2, "105")),
        as_of_date=AS_OF,
        max_age_days=3,
        official_net_flow=Decimal("-20"),
        prior_fund_nav=Decimal("1000"),
    )
    assert result.fund_size_change is None
    assert result.net_flow_ratio == Decimal("-0.02")
    assert result.state is EvidenceState.UNAVAILABLE


def test_csv_evidence_maps_unit_price_and_total_fund_size():
    from datetime import date
    from decimal import Decimal

    from backend.app.funds.international.erste_hungary_f4_adapter import (
        observations_from_csv_evidence,
    )
    from backend.app.funds.international.erste_hungary_f4_csv import (
        CsvEvidence,
        DailyNavRow,
    )

    evidence = CsvEvidence(
        isin="AT0000627476",
        encoding="iso-8859-2",
        delimiter=";",
        header=("Dátum", "Árfolyam", "NEÉ"),
        rows=(
            DailyNavRow(
                date=date(2026, 10, 20),
                price=Decimal("100"),
                nav=Decimal("1000000"),
                turnover=None,
            ),
        ),
        download_bytes=100,
        fund_name="Test fund",
    )

    observations = observations_from_csv_evidence(evidence)

    assert len(observations) == 1
    assert observations[0].unit_price == Decimal("100")
    assert observations[0].fund_size == Decimal("1000000")
    assert observations[0].isin == "AT0000627476"
