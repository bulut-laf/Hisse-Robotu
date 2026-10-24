from decimal import Decimal

from backend.app.funds.international.erste_hungary_rank_seed import (
    build_rank_seed,
    normalize_category,
)


def test_category_normalization():
    assert normalize_category("R\u00e9szv\u00e9ny") == "EQUITY"
    assert normalize_category("K\u00f6tv\u00e9ny") == "BOND"
    assert normalize_category("P\u00e9nzpiaci") == "MONEY_MARKET"
    assert normalize_category("Vegyes") == "MIXED"
    assert normalize_category(None) is None


def test_unknown_category_is_preserved_deterministically():
    assert normalize_category("Speci\u00e1lis strat\u00e9gia") == (
        "OTHER::SPECIALIS STRATEGIA"
    )


def test_rank_seed_orders_within_category():
    rows = build_rank_seed(
        [
            {
                "isin": "HU0000000001",
                "category_raw": "R\u00e9szv\u00e9ny",
                "return_ytd": "0.10",
                "return_1y": "0.20",
                "return_5y": "0.15",
                "volatility_1y": "0.10",
                "max_drawdown_1y": "-0.05",
            },
            {
                "isin": "HU0000000002",
                "category_raw": "R\u00e9szv\u00e9ny",
                "return_ytd": "0.20",
                "return_1y": "0.30",
                "return_5y": "0.25",
                "volatility_1y": "0.10",
                "max_drawdown_1y": "-0.05",
            },
        ]
    )

    by_isin = {row.isin: row for row in rows}

    assert by_isin["HU0000000002"].rank_position == 1
    assert by_isin["HU0000000001"].rank_position == 2
    assert by_isin["HU0000000002"].rank_percentile == Decimal("1")
    assert by_isin["HU0000000001"].rank_percentile == Decimal("0")


def test_missing_returns_do_not_force_rank():
    rows = build_rank_seed(
        [
            {
                "isin": "HU0000000001",
                "category_raw": "K\u00f6tv\u00e9ny",
                "return_ytd": None,
                "return_1y": None,
                "return_5y": None,
            }
        ]
    )

    assert rows[0].rank_score is None
    assert rows[0].rank_position is None
    assert rows[0].rank_percentile is None


def test_categories_rank_independently():
    rows = build_rank_seed(
        [
            {
                "isin": "HU0000000001",
                "category_raw": "R\u00e9szv\u00e9ny",
                "return_1y": "0.10",
            },
            {
                "isin": "HU0000000002",
                "category_raw": "K\u00f6tv\u00e9ny",
                "return_1y": "0.05",
            },
        ]
    )

    assert rows[0].category_size == 1
    assert rows[1].category_size == 1
    assert rows[0].rank_position == 1
    assert rows[1].rank_position == 1

def test_real_erste_categories_are_all_mapped():
    expected = {
        "R\u00e9szv\u00e9ny": "EQUITY",
        "K\u00f6tv\u00e9ny": "BOND",
        "Abszol\u00fat hozam\u00fa": "ABSOLUTE_RETURN",
        "Vegyes": "MIXED",
        "P\u00e9nzpiac": "MONEY_MARKET",
        "Nyersanyag": "COMMODITY",
        "Ingatlan": "REAL_ESTATE",
        "Alapok alapja": "FUND_OF_FUNDS",
        "Sz\u00e1rmaztatott": "DERIVATIVE",
    }

    for raw, normalized in expected.items():
        assert normalize_category(raw) == normalized