from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Mapping, Sequence

from .evidence_mapper import FundEvidenceInput


@dataclass(frozen=True, slots=True)
class FundRiskMetrics:
    identity: str
    volatility: Decimal
    volatility_percentile: Decimal
    max_drawdown: Decimal


def _price(value: Decimal | int | float | str) -> Decimal:
    result = value if isinstance(value, Decimal) else Decimal(str(value))

    if not result.is_finite() or result <= 0:
        raise ValueError("F3_PRICE_MUST_BE_POSITIVE_FINITE")

    return result


def calculate_raw_risk(
    prices: Sequence[Decimal | int | float | str],
) -> tuple[Decimal, Decimal] | None:
    # Minimum 3 prices => 2 daily return observations.
    # Insufficient history is UNAVAILABLE, never forced.
    if len(prices) < 3:
        return None

    values = tuple(_price(x) for x in prices)

    returns = tuple(
        values[index] / values[index - 1] - Decimal("1")
        for index in range(1, len(values))
    )

    mean = sum(returns, Decimal("0")) / Decimal(len(returns))

    variance = (
        sum(
            ((item - mean) ** 2 for item in returns),
            Decimal("0"),
        )
        / Decimal(len(returns))
    )

    volatility = variance.sqrt()

    peak = values[0]
    max_drawdown = Decimal("0")

    for value in values:
        if value > peak:
            peak = value

        drawdown = value / peak - Decimal("1")

        if drawdown < max_drawdown:
            max_drawdown = drawdown

    return volatility, max_drawdown


def _volatility_percentiles(
    raw: Mapping[str, tuple[Decimal, Decimal]],
) -> dict[str, Decimal]:
    if not raw:
        return {}

    ranked = sorted(
        (values[0], identity)
        for identity, values in raw.items()
    )

    count = len(ranked)

    if count == 1:
        return {
            ranked[0][1]: Decimal("0.50")
        }

    output: dict[str, Decimal] = {}

    index = 0

    while index < count:
        volatility = ranked[index][0]
        end = index + 1

        while (
            end < count
            and ranked[end][0] == volatility
        ):
            end += 1

        first_rank = Decimal(index)
        last_rank = Decimal(end - 1)

        average_rank = (
            first_rank + last_rank
        ) / Decimal("2")

        percentile = average_rank / Decimal(count - 1)

        for position in range(index, end):
            output[ranked[position][1]] = percentile

        index = end

    return output


def build_f3_metrics(
    price_histories: Mapping[
        str,
        Sequence[Decimal | int | float | str],
    ],
) -> dict[str, FundRiskMetrics]:
    raw: dict[str, tuple[Decimal, Decimal]] = {}

    for identity in sorted(price_histories):
        if not str(identity).strip():
            raise ValueError("F3_IDENTITY_EMPTY")

        values = calculate_raw_risk(
            price_histories[identity]
        )

        if values is not None:
            raw[identity] = values

    percentiles = _volatility_percentiles(raw)

    return {
        identity: FundRiskMetrics(
            identity=identity,
            volatility=raw[identity][0],
            volatility_percentile=percentiles[identity],
            max_drawdown=raw[identity][1],
        )
        for identity in sorted(raw)
    }


def enrich_f3_evidence_inputs(
    inputs: Sequence[FundEvidenceInput],
    price_histories: Mapping[
        str,
        Sequence[Decimal | int | float | str],
    ],
) -> tuple[FundEvidenceInput, ...]:
    metrics = build_f3_metrics(price_histories)

    result: list[FundEvidenceInput] = []

    for item in inputs:
        metric = metrics.get(
            item.canonical_fund_id
        )

        if metric is None:
            result.append(item)
            continue

        result.append(
            replace(
                item,
                volatility_percentile=(
                    metric.volatility_percentile
                ),
                max_drawdown=metric.max_drawdown,
            )
        )

    return tuple(result)
