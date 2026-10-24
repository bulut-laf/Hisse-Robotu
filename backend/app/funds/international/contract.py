from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import re


INTERNATIONAL_FUND_CONTRACT_VERSION = "international-fund-contract-v1"
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


def normalize_isin(value: object) -> str:
    isin = str(value or "").strip().upper().replace(" ", "")
    if not _ISIN_RE.fullmatch(isin):
        raise ValueError(f"INVALID_ISIN:{isin or 'EMPTY'}")
    return isin


def canonical_isin_fund_id(isin: object) -> str:
    return f"fund:isin:{normalize_isin(isin)}"


def normalize_currency(value: object) -> str | None:
    text = str(value or "").strip().upper()
    return text or None


@dataclass(frozen=True, slots=True)
class InternationalFundSnapshot:
    canonical_fund_id: str
    isin: str
    market: str
    distribution: str
    instrument_type: str

    name: str
    fund_manager: str | None
    category_raw: str | None
    category_normalized: str | None
    currency: str | None
    risk_raw: str | None
    region: str | None

    nav: Decimal | None
    nav_date: date | None
    net_asset_value: Decimal | None
    inception_date: date | None
    settlement: str | None

    return_1m: Decimal | None
    return_3m: Decimal | None
    return_6m: Decimal | None
    return_ytd: Decimal | None
    return_1y: Decimal | None
    return_5y: Decimal | None

    volatility_1y: Decimal | None
    volatility_3y: Decimal | None
    max_drawdown_1y: Decimal | None
    max_drawdown_5y: Decimal | None

    total_expense_ratio: Decimal | None
    allocation_known: bool

    erste_access_status: str | None
    source_url: str
    source_date: date | None
    fetched_at: datetime

    contract_version: str = INTERNATIONAL_FUND_CONTRACT_VERSION
