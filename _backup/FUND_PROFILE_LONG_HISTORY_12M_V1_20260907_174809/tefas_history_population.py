from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .contracts import (
    DataQualityState,
    FundDailyObservation,
)
from .normalization import normalize_fund_code
from .store import FundObservationJsonStore, fund_observation_store
from .tefas_adapter import (
    canonical_tefas_fund_id,
    fetch_tefas_fund_history_rows,
)
from .tefas_history_f3 import parse_tefas_history_rows


DEFAULT_MAXIMUM_FUNDS_PER_BATCH = 50


@dataclass(frozen=True, slots=True)
class TefasHistoryPopulationResult:
    requested_funds: int
    fetched_funds: int
    observation_count: int
    inserted: int
    updated: int
    unchanged: int
    total_records: int


def history_rows_to_observations(
    rows: Iterable[Mapping[str, object]],
    *,
    fund_code: object,
    fetched_at: datetime,
    source_as_of: datetime,
) -> tuple[FundDailyObservation, ...]:
    code = normalize_fund_code(fund_code)

    if fetched_at.tzinfo is None:
        raise ValueError("F3_FETCHED_AT_MUST_BE_TIMEZONE_AWARE")

    if source_as_of.tzinfo is None:
        raise ValueError("F3_SOURCE_AS_OF_MUST_BE_TIMEZONE_AWARE")

    points = parse_tefas_history_rows(
        tuple(rows),
        expected_fund_code=code,
    )

    canonical_id = canonical_tefas_fund_id(code)

    return tuple(
        FundDailyObservation(
            canonical_fund_id=canonical_id,
            observation_date=point.observation_date,
            unit_price=point.unit_price,

            # History endpoint contract has not verified these fields.
            fund_size=None,
            investor_count=None,
            shares_outstanding=None,
            daily_return=None,

            provider="TEFAS",
            fetched_at=fetched_at,
            source_as_of=source_as_of,

            # Price is valid, but daily observation is partial because
            # size/investor/share fields are not supplied by this endpoint.
            data_quality_state=DataQualityState.PARTIAL,
        )
        for point in points
    )


def _normalize_codes(
    fund_codes: Iterable[object],
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()

    for raw in fund_codes:
        code = normalize_fund_code(raw)

        if code in seen:
            continue

        seen.add(code)
        result.append(code)

    return tuple(sorted(result))


def populate_tefas_history_batch(
    fund_codes: Iterable[object],
    *,
    store: FundObservationJsonStore,
    period: int = 1,
    timeout_seconds: int = 10,
    maximum_funds: int = DEFAULT_MAXIMUM_FUNDS_PER_BATCH,
    fetched_at: datetime | None = None,
    source_as_of: datetime | None = None,
) -> TefasHistoryPopulationResult:
    """
    Explicit bounded batch population.

    Important:
    - Does NOT discover/traverse the whole TEFAS universe.
    - Does NOT run from dashboard render.
    - Does NOT create a scheduler.
    - Uses existing FundObservationJsonStore.
    - Fetches all requested histories before one store upsert, so a fetch
      failure does not leave a half-written batch.
    """
    codes = _normalize_codes(fund_codes)

    if not codes:
        raise ValueError("F3_BATCH_EMPTY")

    if maximum_funds < 1:
        raise ValueError("F3_MAXIMUM_FUNDS_INVALID")

    if len(codes) > maximum_funds:
        raise ValueError(
            f"F3_BATCH_LIMIT_EXCEEDED:{len(codes)}>{maximum_funds}"
        )

    now = datetime.now(timezone.utc)

    fetched = fetched_at or now
    source = source_as_of or now

    if fetched.tzinfo is None:
        raise ValueError("F3_FETCHED_AT_MUST_BE_TIMEZONE_AWARE")

    if source.tzinfo is None:
        raise ValueError("F3_SOURCE_AS_OF_MUST_BE_TIMEZONE_AWARE")

    observations: list[FundDailyObservation] = []

    # Fetch phase first. No persistent write yet.
    for code in codes:
        rows = fetch_tefas_fund_history_rows(
            code,
            period=period,
            timeout_seconds=timeout_seconds,
        )

        observations.extend(
            history_rows_to_observations(
                rows,
                fund_code=code,
                fetched_at=fetched,
                source_as_of=source,
            )
        )

    # One idempotent persistent mutation through existing store seam.
    result = store.upsert(
        tuple(observations)
    )

    return TefasHistoryPopulationResult(
        requested_funds=len(codes),
        fetched_funds=len(codes),
        observation_count=len(observations),
        inserted=result.inserted,
        updated=result.updated,
        unchanged=result.unchanged,
        total_records=result.total_records,
    )
def populate_default_tefas_history_batch(
    fund_codes: Iterable[object],
    *,
    period: int = 1,
    timeout_seconds: int = 10,
    maximum_funds: int = DEFAULT_MAXIMUM_FUNDS_PER_BATCH,
    fetched_at: datetime | None = None,
    source_as_of: datetime | None = None,
) -> TefasHistoryPopulationResult:
    """
    Explicit production-store population seam.

    Not called by dashboard rendering.
    Still bounded by maximum_funds.
    """
    return populate_tefas_history_batch(
        fund_codes,
        store=fund_observation_store(),
        period=period,
        timeout_seconds=timeout_seconds,
        maximum_funds=maximum_funds,
        fetched_at=fetched_at,
        source_as_of=source_as_of,
    )
