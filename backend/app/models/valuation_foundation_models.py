from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class OwnershipSnapshot:
    symbol: str
    as_of_date: date
    published_at: datetime | None
    total_shares: Decimal
    free_float_ratio: Decimal | None = None  # 0..1
    effective_free_float_ratio: Decimal | None = None  # 0..1
    treasury_shares: Decimal = Decimal("0")
    diluted_shares: Decimal | None = None
    major_shareholder_ratio: Decimal | None = None  # 0..1
    major_shareholders: tuple[tuple[str, Decimal], ...] = ()
    privileged_share_flag: bool | None = None
    source: str = "KAP/BIST"
    source_ref: str | None = None

    @property
    def canonical_share_count(self) -> Decimal:
        return self.diluted_shares if self.diluted_shares is not None else self.total_shares

    @property
    def free_float_shares(self) -> Decimal | None:
        ratio = self.effective_free_float_ratio
        if ratio is None:
            ratio = self.free_float_ratio
        if ratio is None:
            return None
        return self.total_shares * ratio


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    price_date: date
    price: Decimal
    published_at: datetime | None = None
    source: str = "CANONICAL_MARKET"


@dataclass(frozen=True)
class MultipleSnapshot:
    symbol: str
    as_of_date: date
    pe: Decimal | None
    pb: Decimal | None
    ev_ebitda: Decimal | None
    ev_sales: Decimal | None
    ps: Decimal | None
    p_fcf: Decimal | None
    dividend_yield: Decimal | None
    market_cap: Decimal
    enterprise_value: Decimal | None
    equity_value_basis: Decimal | None
    earnings_basis: Decimal | None
    ebitda_basis: Decimal | None
    revenue_basis: Decimal | None
    fcf_basis: Decimal | None
    data_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelativeValuationResult:
    symbol: str
    as_of_date: date
    current: MultipleSnapshot
    historical_medians: dict[str, Decimal | None]
    historical_discount_premium: dict[str, Decimal | None]
    peer_medians: dict[str, Decimal | None]
    peer_discount_premium: dict[str, Decimal | None]
    confidence: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
