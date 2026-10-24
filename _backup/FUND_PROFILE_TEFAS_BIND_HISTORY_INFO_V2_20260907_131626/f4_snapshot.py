from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, timezone
from decimal import Decimal

from .contracts import DataQualityState, FundDailyObservation
from .normalization import normalize_fund_code, parse_decimal_tr
from .store import FundObservationJsonStore
from .tefas_adapter import (
    canonical_tefas_fund_id,
    fetch_tefas_fund_detail_rows,
)

DEFAULT_MAXIMUM_DETAIL_SNAPSHOT_FUNDS = 50


def _positive_decimal(value: object, field: str) -> Decimal:
    parsed = parse_decimal_tr(value)

    if (
        parsed is None
        or not parsed.is_finite()
        or parsed <= 0
    ):
        raise ValueError(
            f"F4_DETAIL_INVALID_{field}:{value}"
        )

    return parsed


def _investor_count(value: object) -> int:
    parsed = parse_decimal_tr(value)

    if (
        parsed is None
        or not parsed.is_finite()
        or parsed < 0
        or parsed != parsed.to_integral_value()
    ):
        raise ValueError(
            f"F4_DETAIL_INVALID_INVESTOR_COUNT:{value}"
        )

    return int(parsed)


def _detail_row(payload: object) -> Mapping[str, object]:
    if isinstance(payload, Mapping):
        return payload

    rows = tuple(payload)

    if len(rows) != 1:
        raise ValueError(
            f"F4_DETAIL_ROW_COUNT:{len(rows)}"
        )

    row = rows[0]

    if not isinstance(row, Mapping):
        raise ValueError(
            "F4_DETAIL_ROW_INVALID"
        )

    return row


def detail_row_to_observation(
    row: Mapping[str, object],
    *,
    expected_fund_code: object,
    fetched_at: datetime,
    observation_date: date | None = None,
) -> FundDailyObservation:
    if fetched_at.tzinfo is None:
        raise ValueError(
            "F4_FETCHED_AT_TIMEZONE_REQUIRED"
        )

    expected = normalize_fund_code(
        expected_fund_code
    )

    actual = normalize_fund_code(
        row.get("fonKodu")
    )

    if actual != expected:
        raise ValueError(
            f"F4_DETAIL_FUND_MISMATCH:"
            f"{expected}:{actual}"
        )

    unit_price = _positive_decimal(
        row.get("sonFiyat"),
        "sonFiyat",
    )

    fund_size = _positive_decimal(
        row.get("portBuyukluk"),
        "portBuyukluk",
    )

    investors = _investor_count(
        row.get("yatirimciSayi")
    )

    shares = parse_decimal_tr(
        row.get("payAdet")
    )

    if (
        shares is not None
        and (
            not shares.is_finite()
            or shares < 0
        )
    ):
        raise ValueError(
            "F4_DETAIL_INVALID_PAY_ADET"
        )

    daily_return = parse_decimal_tr(
        row.get("gunlukGetiri"),
        percent=True,
    )

    # IMPORTANT:
    # FundDailyObservation rejects dates beyond UTC today.
    # Therefore canonical observation_date follows UTC date,
    # not Europe/Istanbul wall-calendar date.
    observed = (
        observation_date
        if observation_date is not None
        else fetched_at.astimezone(
            timezone.utc
        ).date()
    )

    return FundDailyObservation(
        canonical_fund_id=(
            canonical_tefas_fund_id(expected)
        ),
        observation_date=observed,
        unit_price=unit_price,
        fund_size=fund_size,
        investor_count=investors,
        shares_outstanding=shares,
        daily_return=daily_return,
        provider="TEFAS",
        fetched_at=fetched_at,
        source_as_of=fetched_at,
        data_quality_state=DataQualityState.VALID,
    )


def fetch_tefas_detail_observation(
    fund_code: object,
    *,
    fetched_at: datetime | None = None,
    observation_date: date | None = None,
) -> FundDailyObservation:
    code = normalize_fund_code(
        fund_code
    )

    stamp = (
        fetched_at
        if fetched_at is not None
        else datetime.now(timezone.utc)
    )

    payload = fetch_tefas_fund_detail_rows(
        code
    )

    return detail_row_to_observation(
        _detail_row(payload),
        expected_fund_code=code,
        fetched_at=stamp,
        observation_date=observation_date,
    )


def snapshot_tefas_detail_batch(
    fund_codes: Iterable[object],
    *,
    store: FundObservationJsonStore,
    maximum_funds: int = DEFAULT_MAXIMUM_DETAIL_SNAPSHOT_FUNDS,
    fetched_at: datetime | None = None,
    observation_date: date | None = None,
):
    codes = tuple(
        sorted(
            {
                normalize_fund_code(code)
                for code in fund_codes
            }
        )
    )

    if not codes:
        raise ValueError(
            "F4_DETAIL_BATCH_EMPTY"
        )

    if len(codes) > maximum_funds:
        raise ValueError(
            f"F4_DETAIL_BATCH_LIMIT:"
            f"{len(codes)}>{maximum_funds}"
        )

    stamp = (
        fetched_at
        if fetched_at is not None
        else datetime.now(timezone.utc)
    )

    # Bounded explicit operation:
    # fetch first -> one store write.
    observations = tuple(
        fetch_tefas_detail_observation(
            code,
            fetched_at=stamp,
            observation_date=observation_date,
        )
        for code in codes
    )

    return store.upsert(
        observations
    )
