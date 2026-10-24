from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation

from .evidence_mapper import (
    FundEvidenceInput,
    FundEvidenceMap,
    map_fund_evidence,
)
from .store import FundObservationJsonStore


@dataclass(frozen=True, slots=True)
class FundFlowMetrics:
    canonical_fund_id: str
    previous_date: date
    latest_date: date
    fund_size_change: Decimal
    investor_change: Decimal | None
    net_flow_ratio: Decimal | None = None


def _decimal(value: object, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (
        InvalidOperation,
        ValueError,
    ) as exc:
        raise ValueError(
            f"F4_STORE_INVALID_{field}:{value}"
        ) from exc

    if not parsed.is_finite():
        raise ValueError(
            f"F4_STORE_INVALID_{field}:{value}"
        )

    return parsed


def flow_metrics_from_store(
    store: FundObservationJsonStore,
    *,
    canonical_fund_ids: Iterable[str] | None = None,
) -> dict[str, FundFlowMetrics]:
    wanted = (
        set(canonical_fund_ids)
        if canonical_fund_ids is not None
        else None
    )

    grouped = {}

    for raw in store.list_records():
        if raw.get("record_type") != "FundDailyObservation":
            continue

        if raw.get("provider") != "TEFAS":
            continue

        fund_id = str(
            raw.get("canonical_fund_id") or ""
        ).strip()

        if not fund_id:
            raise ValueError(
                "F4_STORE_CANONICAL_ID_EMPTY"
            )

        if wanted is not None and fund_id not in wanted:
            continue

        # F3 history-only records are ignored.
        if (
            raw.get("fund_size") in (None, "")
            or raw.get("investor_count") in (None, "")
        ):
            continue

        try:
            observed = date.fromisoformat(
                str(raw.get("observation_date"))
            )
        except Exception as exc:
            raise ValueError(
                "F4_STORE_INVALID_DATE"
            ) from exc

        size = _decimal(
            raw.get("fund_size"),
            "FUND_SIZE",
        )

        investors = _decimal(
            raw.get("investor_count"),
            "INVESTOR_COUNT",
        )

        if size <= 0:
            raise ValueError(
                "F4_STORE_NONPOSITIVE_FUND_SIZE"
            )

        if investors < 0:
            raise ValueError(
                "F4_STORE_NEGATIVE_INVESTOR_COUNT"
            )

        grouped.setdefault(
            fund_id,
            [],
        ).append(
            (
                observed,
                size,
                investors,
            )
        )

    result = {}

    for fund_id, observations in grouped.items():
        ordered = sorted(
            observations,
            key=lambda x: x[0],
        )

        if len(ordered) < 2:
            continue

        prev_date, prev_size, prev_inv = ordered[-2]
        last_date, last_size, last_inv = ordered[-1]

        size_change = (
            last_size / prev_size
            - Decimal("1")
        )

        investor_change = (
            last_inv / prev_inv
            - Decimal("1")
            if prev_inv > 0
            else None
        )

        result[fund_id] = FundFlowMetrics(
            canonical_fund_id=fund_id,
            previous_date=prev_date,
            latest_date=last_date,
            fund_size_change=size_change,
            investor_change=investor_change,
            # Deliberately unavailable.
            net_flow_ratio=None,
        )

    return result


def f4_evidence_from_store(
    store: FundObservationJsonStore,
    *,
    canonical_fund_ids: Iterable[str],
) -> dict[str, object]:
    ids = tuple(
        sorted(
            set(canonical_fund_ids)
        )
    )

    metrics = flow_metrics_from_store(
        store,
        canonical_fund_ids=ids,
    )

    result = {}

    for fund_id, metric in metrics.items():
        mapped = map_fund_evidence(
            FundEvidenceInput(
                canonical_fund_id=fund_id,
                category_id=None,
                category_rank_percentile=None,
                category_rank_change=None,
                return_1m=None,
                return_3m=None,
                return_6m=None,
                volatility_percentile=None,
                max_drawdown=None,
                fund_size_change=metric.fund_size_change,
                investor_change=metric.investor_change,
                net_flow_ratio=None,
                total_expense_ratio=None,
                regime_fit=None,
                allocation_known=False,
            )
        )

        result[fund_id] = next(
            evidence
            for evidence in mapped.evidence
            if evidence.family == "F4"
        )

    return result


def enrich_evidence_maps_with_f4_store(
    evidence_maps: Iterable[FundEvidenceMap],
    *,
    store: FundObservationJsonStore,
) -> tuple[FundEvidenceMap, ...]:
    items = tuple(evidence_maps)

    f4_by_id = f4_evidence_from_store(
        store,
        canonical_fund_ids=(
            item.canonical_fund_id
            for item in items
        ),
    )

    output = []

    for item in items:
        replacement = f4_by_id.get(
            item.canonical_fund_id
        )

        if replacement is None:
            output.append(item)
            continue

        output.append(
            replace(
                item,
                evidence=tuple(
                    replacement
                    if current.family == "F4"
                    else current
                    for current in item.evidence
                ),
            )
        )

    return tuple(output)
