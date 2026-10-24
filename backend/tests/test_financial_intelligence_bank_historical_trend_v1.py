from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.analysis.financial_intelligence_bank_historical_trend import (
    build_bank_historical_trend,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("symbol", "expected_score", "expected_publication"),
    (
        (
            "AKBNK",
            73.43313615836219,
            "2026-07-28",
        ),
        (
            "GARAN",
            76.54726792009401,
            "2026-07-30",
        ),
    ),
)
def test_real_bank_bundle_builds_single_historical_snapshot(
    symbol,
    expected_score,
    expected_publication,
):
    trend = build_bank_historical_trend(
        PROJECT_ROOT,
        symbol,
    )

    assert trend.symbol == symbol
    assert trend.read_only is True

    # At the moment there is only one official
    # production bundle for each bank: 2026Q2.
    assert len(trend.snapshots) == 1

    snapshot = trend.snapshots[0]

    assert snapshot.symbol == symbol
    assert snapshot.period_end == "2026-06-30"
    assert snapshot.publication_date == expected_publication
    assert snapshot.as_of == expected_publication

    assert snapshot.total_score == pytest.approx(
        expected_score
    )

    assert (
        snapshot.model_version
        == "BANK_SCORING_ENGINE_V1"
    )

    assert snapshot.read_only is True

    assert len(snapshot.canonical_facts) == 13
    assert snapshot.component_scores
    assert snapshot.metric_scores


def test_akbnk_historical_metrics_are_real_canonical_facts():
    trend = build_bank_historical_trend(
        PROJECT_ROOT,
        "AKBNK",
    )

    facts = trend.snapshots[0].canonical_facts

    assert Decimal(
        str(
            facts[
                "CAPITAL_ADEQUACY.capital_adequacy_ratio"
            ]
        )
    ) == Decimal("16.38")

    assert Decimal(
        str(
            facts[
                "PROFITABILITY.roe"
            ]
        )
    ) == Decimal("22.2")

    assert Decimal(
        str(
            facts[
                "PROFITABILITY.net_interest_margin"
            ]
        )
    ) == Decimal("5.1")


def test_garan_historical_metrics_are_real_canonical_facts():
    trend = build_bank_historical_trend(
        PROJECT_ROOT,
        "GARAN",
    )

    facts = trend.snapshots[0].canonical_facts

    assert Decimal(
        str(
            facts[
                "CAPITAL_ADEQUACY.capital_adequacy_ratio"
            ]
        )
    ) == Decimal("15.90")

    assert Decimal(
        str(
            facts[
                "PROFITABILITY.roe"
            ]
        )
    ) == Decimal("28.10")

    assert Decimal(
        str(
            facts[
                "PROFITABILITY.net_interest_margin"
            ]
        )
    ) == Decimal("5.70")


def test_unknown_symbol_has_empty_history():
    trend = build_bank_historical_trend(
        PROJECT_ROOT,
        "ZZZZZ",
    )

    assert trend.symbol == "ZZZZZ"
    assert trend.snapshots == ()
    assert trend.read_only is True


def test_historical_model_contains_no_trade_authority():
    trend = build_bank_historical_trend(
        PROJECT_ROOT,
        "GARAN",
    )

    snapshot = trend.snapshots[0]

    forbidden = {
        "buy",
        "sell",
        "trade",
        "recommendation",
        "ranking",
        "target_price",
        "entry_price",
        "position_size",
    }

    assert forbidden.isdisjoint(
        snapshot.__dataclass_fields__.keys()
    )