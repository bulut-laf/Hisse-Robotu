from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Sequence

from .evidence_mapper import FundEvidenceInput
from .normalization import parse_decimal_tr
from .risk_metrics import enrich_f3_evidence_inputs
from .tefas_adapter import (
    fetch_tefas_fund_history_rows,
    normalize_fund_code,
)


@dataclass(frozen=True, slots=True)
class TefasFundPricePoint:
    fund_code: str
    observation_date: date
    unit_price: Decimal


_REQUIRED_HISTORY_FIELDS = (
    "fonKodu",
    "tarih",
    "fiyat",
)


def parse_tefas_history_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    expected_fund_code: object | None = None,
) -> tuple[TefasFundPricePoint, ...]:
    expected = (
        normalize_fund_code(expected_fund_code)
        if expected_fund_code is not None
        else ""
    )

    output: list[TefasFundPricePoint] = []
    seen_dates: set[date] = set()
    observed_code: str | None = None

    for row in rows:
        missing = [
            field
            for field in _REQUIRED_HISTORY_FIELDS
            if field not in row
        ]

        if missing:
            raise ValueError(
                "F3_HISTORY_SCHEMA_MISSING:"
                + ",".join(missing)
            )

        code = normalize_fund_code(
            row.get("fonKodu")
        )

        if not code:
            raise ValueError(
                "F3_HISTORY_FUND_CODE_EMPTY"
            )

        if expected and code != expected:
            raise ValueError(
                f"F3_HISTORY_FUND_MISMATCH:{expected}:{code}"
            )

        if observed_code is None:
            observed_code = code
        elif observed_code != code:
            raise ValueError(
                "F3_HISTORY_MIXED_FUND_CODES"
            )

        try:
            observed = date.fromisoformat(
                str(row["tarih"]).strip()
            )
        except Exception as exc:
            raise ValueError(
                f"F3_HISTORY_INVALID_DATE:{row.get('tarih')}"
            ) from exc

        if observed in seen_dates:
            raise ValueError(
                f"F3_HISTORY_DUPLICATE_DATE:"
                f"{code}:{observed.isoformat()}"
            )

        seen_dates.add(observed)

        # Invalid/missing/nonpositive price is unavailable evidence.
        # It is NOT converted to zero and is NOT filled.
        try:
            price = parse_decimal_tr(
                row.get("fiyat")
            )
        except (ValueError, TypeError):
            continue

        if (
            price is None
            or not price.is_finite()
            or price <= 0
        ):
            continue

        output.append(
            TefasFundPricePoint(
                fund_code=code,
                observation_date=observed,
                unit_price=price,
            )
        )

    return tuple(
        sorted(
            output,
            key=lambda item: item.observation_date,
        )
    )


def price_series_from_tefas_history_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    expected_fund_code: object | None = None,
) -> tuple[Decimal, ...]:
    return tuple(
        point.unit_price
        for point in parse_tefas_history_rows(
            rows,
            expected_fund_code=expected_fund_code,
        )
    )


def fetch_tefas_price_series(
    fund_code: object,
    *,
    period: int = 1,
    timeout_seconds: int = 10,
) -> tuple[Decimal, ...]:
    code = normalize_fund_code(fund_code)

    if not code:
        raise ValueError("fund_code boş olamaz.")

    rows = fetch_tefas_fund_history_rows(
        code,
        period=period,
        timeout_seconds=timeout_seconds,
    )

    return price_series_from_tefas_history_rows(
        rows,
        expected_fund_code=code,
    )


def enrich_f3_inputs_from_tefas_histories(
    inputs_by_fund_code: Mapping[
        str,
        FundEvidenceInput,
    ],
    history_rows_by_fund_code: Mapping[
        str,
        Sequence[Mapping[str, object]],
    ],
) -> tuple[FundEvidenceInput, ...]:
    normalized_histories: dict[
        str,
        Sequence[Mapping[str, object]],
    ] = {}

    for raw_code, rows in history_rows_by_fund_code.items():
        code = normalize_fund_code(raw_code)

        if not code:
            raise ValueError(
                "F3_HISTORY_MAPPING_CODE_EMPTY"
            )

        if code in normalized_histories:
            raise ValueError(
                f"F3_HISTORY_MAPPING_DUPLICATE:{code}"
            )

        normalized_histories[code] = rows

    ordered_inputs: list[FundEvidenceInput] = []
    histories_by_canonical_id: dict[
        str,
        tuple[Decimal, ...],
    ] = {}

    normalized_inputs: list[
        tuple[str, FundEvidenceInput]
    ] = []

    for raw_code, item in inputs_by_fund_code.items():
        code = normalize_fund_code(raw_code)

        if not code:
            raise ValueError(
                "F3_INPUT_CODE_EMPTY"
            )

        normalized_inputs.append(
            (code, item)
        )

    for code, item in sorted(
        normalized_inputs,
        key=lambda value: value[0],
    ):
        ordered_inputs.append(item)

        rows = normalized_histories.get(code)

        if rows is None:
            # No history => F3 remains unavailable.
            continue

        histories_by_canonical_id[
            item.canonical_fund_id
        ] = price_series_from_tefas_history_rows(
            rows,
            expected_fund_code=code,
        )

    return enrich_f3_evidence_inputs(
        tuple(ordered_inputs),
        histories_by_canonical_id,
    )


def fetch_and_enrich_f3_inputs(
    inputs_by_fund_code: Mapping[
        str,
        FundEvidenceInput,
    ],
    *,
    period: int = 1,
    timeout_seconds: int = 10,
) -> tuple[FundEvidenceInput, ...]:
    """
    Explicit callable only.

    It is NOT mounted to dashboard render and does not automatically
    traverse the 2137-fund universe.
    """
    histories: dict[
        str,
        Sequence[Mapping[str, object]],
    ] = {}

    for raw_code in sorted(inputs_by_fund_code):
        code = normalize_fund_code(raw_code)

        if not code:
            raise ValueError(
                "F3_INPUT_CODE_EMPTY"
            )

        histories[code] = fetch_tefas_fund_history_rows(
            code,
            period=period,
            timeout_seconds=timeout_seconds,
        )

    return enrich_f3_inputs_from_tefas_histories(
        inputs_by_fund_code,
        histories,
    )
