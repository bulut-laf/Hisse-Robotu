from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from datetime import date
from decimal import Decimal, InvalidOperation

from .analysis_engine import FundAnalysisResult, analyze_funds
from .evidence_mapper import (
    FundEvidenceInput,
    FundEvidenceMap,
    map_fund_evidence,
)
from .live_pipeline import evidence_from_tefas_rows
from .risk_metrics import build_f3_metrics
from .store import FundObservationJsonStore


def _stored_price(value: object) -> Decimal:
    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(
            f"F3_STORE_INVALID_PRICE:{value}"
        ) from exc

    if not price.is_finite() or price <= 0:
        raise ValueError(
            f"F3_STORE_INVALID_PRICE:{value}"
        )

    return price


def price_histories_from_store(
    store: FundObservationJsonStore,
    *,
    canonical_fund_ids: Iterable[str] | None = None,
) -> dict[str, tuple[Decimal, ...]]:
    wanted = (
        set(canonical_fund_ids)
        if canonical_fund_ids is not None
        else None
    )

    grouped: dict[
        str,
        list[tuple[date, Decimal]],
    ] = {}

    seen: set[tuple[str, date]] = set()

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
                "F3_STORE_CANONICAL_ID_EMPTY"
            )

        if wanted is not None and fund_id not in wanted:
            continue

        raw_price = raw.get("unit_price")

        if raw_price in (None, ""):
            # Missing price cannot contribute to F3.
            continue

        try:
            observed = date.fromisoformat(
                str(raw.get("observation_date"))
            )
        except Exception as exc:
            raise ValueError(
                "F3_STORE_INVALID_OBSERVATION_DATE"
            ) from exc

        key = (
            fund_id,
            observed,
        )

        if key in seen:
            raise ValueError(
                f"F3_STORE_DUPLICATE_OBSERVATION:"
                f"{fund_id}:{observed.isoformat()}"
            )

        seen.add(key)

        grouped.setdefault(
            fund_id,
            [],
        ).append(
            (
                observed,
                _stored_price(raw_price),
            )
        )

    return {
        fund_id: tuple(
            price
            for _, price in sorted(
                observations,
                key=lambda item: item[0],
            )
        )
        for fund_id, observations
        in sorted(grouped.items())
    }


def f3_evidence_from_store(
    store: FundObservationJsonStore,
    *,
    canonical_fund_ids: Iterable[str],
) -> dict[str, object]:
    fund_ids = tuple(
        sorted(set(canonical_fund_ids))
    )

    histories = price_histories_from_store(
        store,
        canonical_fund_ids=fund_ids,
    )

    metrics = build_f3_metrics(
        histories
    )

    result: dict[str, object] = {}

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

                volatility_percentile=(
                    metric.volatility_percentile
                ),
                max_drawdown=(
                    metric.max_drawdown
                ),

                fund_size_change=None,
                investor_change=None,
                net_flow_ratio=None,

                total_expense_ratio=None,
                regime_fit=None,
                allocation_known=False,
            )
        )

        f3 = next(
            item
            for item in mapped.evidence
            if item.family == "F3"
        )

        result[fund_id] = f3

    return result


def enrich_evidence_maps_with_f3_store(
    evidence_maps: Iterable[FundEvidenceMap],
    *,
    store: FundObservationJsonStore,
) -> tuple[FundEvidenceMap, ...]:
    items = tuple(evidence_maps)

    f3_by_id = f3_evidence_from_store(
        store,
        canonical_fund_ids=(
            item.canonical_fund_id
            for item in items
        ),
    )

    output: list[FundEvidenceMap] = []

    for item in items:
        replacement = f3_by_id.get(
            item.canonical_fund_id
        )

        if replacement is None:
            # No sufficient persisted history:
            # preserve existing F3 UNAVAILABLE.
            output.append(item)
            continue

        evidence = tuple(
            replacement
            if current.family == "F3"
            else current
            for current in item.evidence
        )

        output.append(
            replace(
                item,
                evidence=evidence,
            )
        )

    return tuple(output)


def analyze_tefas_rows_with_f3_store(
    rows: Iterable[Mapping[str, object]],
    *,
    store: FundObservationJsonStore,
) -> tuple[FundAnalysisResult, ...]:
    """
    Existing live F2 mapping
      -> persisted F3 enrichment
      -> existing analyze_funds()

    No network call is performed by this function.
    """
    base = evidence_from_tefas_rows(
        rows
    )

    enriched = enrich_evidence_maps_with_f3_store(
        base,
        store=store,
    )

    return analyze_funds(
        enriched
    )
