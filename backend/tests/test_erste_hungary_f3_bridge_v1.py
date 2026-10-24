from decimal import Decimal

from backend.app.funds.international.erste_hungary_f3_bridge import (
    build_f1_f3_input,
    category_volatility_percentiles,
    mapped_f3_state,
)


def test_category_volatility_percentile_low_is_better():
    rows = [
        {"isin": "A", "category_normalized": "EQUITY", "volatility_1y": "0.10"},
        {"isin": "B", "category_normalized": "EQUITY", "volatility_1y": "0.20"},
        {"isin": "C", "category_normalized": "EQUITY", "volatility_1y": "0.30"},
    ]

    result = category_volatility_percentiles(rows)

    assert result["A"] == Decimal("0")
    assert result["B"] == Decimal("0.5")
    assert result["C"] == Decimal("1")


def test_f3_positive_for_low_vol_and_shallow_drawdown():
    value = build_f1_f3_input(
        isin="LU0000000001",
        category_normalized="EQUITY",
        category_rank_percentile=Decimal("0.8"),
        category_rank_change=2,
        volatility_percentile=Decimal("0.2"),
        max_drawdown_1y=Decimal("-0.08"),
    )

    assert mapped_f3_state(value) == "EvidenceState.POSITIVE"


def test_f3_caution_for_high_volatility():
    value = build_f1_f3_input(
        isin="LU0000000002",
        category_normalized="EQUITY",
        category_rank_percentile=Decimal("0.8"),
        category_rank_change=2,
        volatility_percentile=Decimal("0.9"),
        max_drawdown_1y=Decimal("-0.08"),
    )

    assert mapped_f3_state(value) == "EvidenceState.CAUTION"


def test_missing_drawdown_keeps_f3_unavailable():
    value = build_f1_f3_input(
        isin="LU0000000003",
        category_normalized="BOND",
        category_rank_percentile=Decimal("0.5"),
        category_rank_change=0,
        volatility_percentile=Decimal("0.3"),
        max_drawdown_1y=None,
    )

    assert mapped_f3_state(value) == "EvidenceState.UNAVAILABLE"

def test_unicode_category_names_are_preserved_by_python_source():
    category_map = {
        "R\u00e9szv\u00e9ny": "EQUITY",
        "K\u00f6tv\u00e9ny": "BOND",
        "Abszol\u00fat hozam\u00fa": "ABSOLUTE_RETURN",
        "P\u00e9nzpiac": "MONEY_MARKET",
        "Sz\u00e1rmaztatott": "DERIVATIVE",
    }

    assert category_map["R\u00e9szv\u00e9ny"] == "EQUITY"
    assert category_map["K\u00f6tv\u00e9ny"] == "BOND"
    assert category_map["Abszol\u00fat hozam\u00fa"] == "ABSOLUTE_RETURN"
    assert category_map["P\u00e9nzpiac"] == "MONEY_MARKET"
    assert category_map["Sz\u00e1rmaztatott"] == "DERIVATIVE"