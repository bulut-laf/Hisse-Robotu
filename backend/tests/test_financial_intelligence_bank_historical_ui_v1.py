from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.ui.financial_intelligence_dashboard import (
    _build_bank_historical_rows,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("symbol", "score", "publication"),
    (
        (
            "AKBNK",
            73.43,
            "2026-07-28",
        ),
        (
            "GARAN",
            76.55,
            "2026-07-30",
        ),
    ),
)
def test_real_bank_history_builds_ui_row(
    symbol,
    score,
    publication,
):
    rows = _build_bank_historical_rows(
        PROJECT_ROOT,
        symbol,
    )

    assert len(rows) == 1

    row = rows[0]

    assert row["Dönem"] == "2026-06-30"
    assert row["Yayın Tarihi"] == publication
    assert row["BANK Skoru"] == pytest.approx(score)


def test_akbnk_ui_row_contains_real_metrics():
    row = _build_bank_historical_rows(
        PROJECT_ROOT,
        "AKBNK",
    )[0]

    assert Decimal(
        str(row["CAR %"])
    ) == Decimal("16.38")

    assert Decimal(
        str(row["ROE %"])
    ) == Decimal("22.2")

    assert Decimal(
        str(row["NIM %"])
    ) == Decimal("5.1")


def test_garan_ui_row_contains_real_metrics():
    row = _build_bank_historical_rows(
        PROJECT_ROOT,
        "GARAN",
    )[0]

    assert Decimal(
        str(row["CAR %"])
    ) == Decimal("15.90")

    assert Decimal(
        str(row["ROE %"])
    ) == Decimal("28.10")

    assert Decimal(
        str(row["NIM %"])
    ) == Decimal("5.70")


def test_unknown_symbol_has_no_historical_rows():
    rows = _build_bank_historical_rows(
        PROJECT_ROOT,
        "ZZZZZ",
    )

    assert rows == []


def test_historical_ui_has_no_trade_fields():
    row = _build_bank_historical_rows(
        PROJECT_ROOT,
        "GARAN",
    )[0]

    forbidden = {
        "AL",
        "SAT",
        "Recommendation",
        "Target Price",
        "Entry Price",
        "Ranking",
        "Position Size",
    }

    assert forbidden.isdisjoint(row.keys())