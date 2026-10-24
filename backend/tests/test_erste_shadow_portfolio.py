from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from backend.app.funds.erste_shadow_portfolio import ErsteShadowPortfolioStore


def snapshot(isin="HU0000701685", nav="10.0", currency="EUR", nav_date=date(2026, 10, 21)):
    return SimpleNamespace(
        canonical_fund_id=f"fund:isin:{isin}",
        isin=isin,
        name="Example Erste Fund",
        currency=currency,
        nav=Decimal(nav),
        nav_date=nav_date,
        source_url="https://example.invalid/fund",
        source_date=date(2026, 10, 21),
        erste_access_status="VERIFIED",
    )


class TestErsteShadowPortfolio(unittest.TestCase):
    def test_adds_only_explicitly_sale_eligible_funds(self):
        with TemporaryDirectory() as tmp:
            store = ErsteShadowPortfolioStore(Path(tmp) / "funds.json")
            result = store.add_verified_funds(
                [snapshot()], sale_eligible_isins={"HU0000701685"}
            )
            self.assertEqual(len(result.positions), 1)
            self.assertTrue(result.positions[0].sale_eligibility_confirmed)
            self.assertEqual(result.execution_authority, "NONE")
            self.assertEqual(result.positions[0].initial_value_local, "100")

    def test_missing_snapshot_for_eligible_fund_fails_closed(self):
        with TemporaryDirectory() as tmp:
            store = ErsteShadowPortfolioStore(Path(tmp) / "funds.json")
            with self.assertRaisesRegex(ValueError, "ELIGIBLE_FUND_SNAPSHOT_MISSING"):
                store.add_verified_funds([], sale_eligible_isins={"HU0000701685"})

    def test_missing_nav_date_fails_closed(self):
        with TemporaryDirectory() as tmp:
            store = ErsteShadowPortfolioStore(Path(tmp) / "funds.json")
            with self.assertRaisesRegex(ValueError, "NAV_DATE_MISSING"):
                store.add_verified_funds(
                    [snapshot(nav_date=None)], sale_eligible_isins={"HU0000701685"}
                )

    def test_non_positive_nav_fails_closed(self):
        with TemporaryDirectory() as tmp:
            store = ErsteShadowPortfolioStore(Path(tmp) / "funds.json")
            with self.assertRaisesRegex(ValueError, "NON_POSITIVE_NAV"):
                store.add_verified_funds(
                    [snapshot(nav="0")], sale_eligible_isins={"HU0000701685"}
                )

    def test_update_nav_calculates_local_currency_return(self):
        with TemporaryDirectory() as tmp:
            store = ErsteShadowPortfolioStore(Path(tmp) / "funds.json")
            store.add_verified_funds(
                [snapshot()], sale_eligible_isins={"HU0000701685"}
            )
            result = store.update_nav(
                "HU0000701685", "11", date(2026, 10, 22),
                source_url="https://example.invalid/updated",
            )
            self.assertEqual(Decimal(result.positions[0].currency_return_pct), Decimal("10.0"))
            self.assertEqual(result.positions[0].latest_nav_date, "2026-10-22")

    def test_different_currencies_are_not_combined(self):
        with TemporaryDirectory() as tmp:
            store = ErsteShadowPortfolioStore(Path(tmp) / "funds.json")
            result = store.add_verified_funds(
                [snapshot(), snapshot("HU0000702717", "200", "HUF")],
                sale_eligible_isins={"HU0000701685", "HU0000702717"},
            )
            self.assertEqual(
                result.currency_policy, "SEPARATE_CURRENCY_BUCKETS_NO_FX_CONVERSION"
            )
            self.assertEqual({p.currency for p in result.positions}, {"EUR", "HUF"})

    def test_stock_portfolio_path_is_not_used(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "erste_golge_portfoy_v1.json"
            store = ErsteShadowPortfolioStore(path)
            store.add_verified_funds(
                [snapshot()], sale_eligible_isins={"HU0000701685"}
            )
            self.assertTrue(path.exists())
            self.assertNotEqual(path.name, "golge_portfoy.json")


if __name__ == "__main__":
    unittest.main()
