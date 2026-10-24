from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import json


class MarketOwnershipCanonicalError(ValueError):
    pass


def _d(value) -> Decimal | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _iso_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))


def _iso_dt(value) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _ratio(value, name: str) -> Decimal | None:
    x = _d(value)
    if x is None:
        return None
    # JSON contract may use either 0..1 or human percentage 0..100.
    if x > 1:
        x = x / Decimal("100")
    if not (Decimal("0") <= x <= Decimal("1")):
        raise MarketOwnershipCanonicalError(f"{name} must be 0..1 or 0..100")
    return x


@dataclass(frozen=True)
class CanonicalMarketOwnershipInput:
    symbol: str
    as_of_date: date
    published_at: datetime | None

    # IMPORTANT BIST convention:
    # valuation_units are 1 TRY nominal lot-equivalent units used for quoted
    # price × units = market-cap calculations. This is intentionally distinct
    # from the legal number of certificate/share pieces when nominal value
    # per legal share differs from TRY 1.
    issued_capital_try: Decimal
    quote_nominal_unit_try: Decimal
    valuation_units: Decimal

    legal_share_nominal_try: Decimal | None = None
    legal_share_piece_count: Decimal | None = None

    free_float_ratio: Decimal | None = None
    effective_free_float_ratio: Decimal | None = None
    controlling_group_ratio: Decimal | None = None
    treasury_valuation_units: Decimal = Decimal("0")
    diluted_valuation_units: Decimal | None = None
    privileged_share_flag: bool | None = None

    price_try: Decimal | None = None
    price_date: date | None = None
    price_published_at: datetime | None = None

    ownership_source: str = "KAP/MKK"
    ownership_source_ref: str | None = None
    market_source: str = "CANONICAL_MARKET"
    market_source_ref: str | None = None
    schema_version: str = "fin-prod-002-v1"

    def validate(self) -> None:
        if not self.symbol.strip():
            raise MarketOwnershipCanonicalError("symbol is required")
        if self.issued_capital_try <= 0:
            raise MarketOwnershipCanonicalError("issued_capital_try must be positive")
        if self.quote_nominal_unit_try <= 0:
            raise MarketOwnershipCanonicalError("quote_nominal_unit_try must be positive")
        expected = self.issued_capital_try / self.quote_nominal_unit_try
        if abs(expected - self.valuation_units) > Decimal("0.0001"):
            raise MarketOwnershipCanonicalError(
                f"valuation_units mismatch: expected {expected}, got {self.valuation_units}"
            )
        if self.legal_share_nominal_try is not None and self.legal_share_nominal_try <= 0:
            raise MarketOwnershipCanonicalError("legal_share_nominal_try must be positive")
        if self.legal_share_piece_count is not None and self.legal_share_piece_count <= 0:
            raise MarketOwnershipCanonicalError("legal_share_piece_count must be positive")
        if self.treasury_valuation_units < 0 or self.treasury_valuation_units > self.valuation_units:
            raise MarketOwnershipCanonicalError("treasury_valuation_units out of range")
        if self.diluted_valuation_units is not None and self.diluted_valuation_units <= 0:
            raise MarketOwnershipCanonicalError("diluted_valuation_units must be positive")
        for name in ("free_float_ratio", "effective_free_float_ratio", "controlling_group_ratio"):
            x = getattr(self, name)
            if x is not None and not (Decimal("0") <= x <= Decimal("1")):
                raise MarketOwnershipCanonicalError(f"{name} out of range")
        if self.price_try is not None and self.price_try <= 0:
            raise MarketOwnershipCanonicalError("price_try must be positive")
        if self.price_try is not None and self.price_date is None:
            raise MarketOwnershipCanonicalError("price_date required when price_try is provided")
        if self.published_at is not None and self.published_at.date() < self.as_of_date:
            # Allowed for source records only if source publication is later than effective date.
            pass

    @property
    def canonical_valuation_units(self) -> Decimal:
        return self.diluted_valuation_units or self.valuation_units

    @property
    def effective_float_ratio(self) -> Decimal | None:
        return self.effective_free_float_ratio if self.effective_free_float_ratio is not None else self.free_float_ratio

    @property
    def free_float_valuation_units(self) -> Decimal | None:
        r = self.effective_float_ratio
        return None if r is None else self.valuation_units * r

    @property
    def market_cap_try(self) -> Decimal | None:
        return None if self.price_try is None else self.price_try * self.canonical_valuation_units

    @property
    def free_float_market_cap_try(self) -> Decimal | None:
        if self.price_try is None or self.free_float_valuation_units is None:
            return None
        return self.price_try * self.free_float_valuation_units


def from_dict(raw: dict) -> CanonicalMarketOwnershipInput:
    obj = CanonicalMarketOwnershipInput(
        symbol=str(raw["symbol"]).upper(),
        as_of_date=_iso_date(raw["as_of_date"]),
        published_at=_iso_dt(raw.get("published_at")),
        issued_capital_try=_d(raw["issued_capital_try"]),
        quote_nominal_unit_try=_d(raw.get("quote_nominal_unit_try", "1")),
        valuation_units=_d(raw["valuation_units"]),
        legal_share_nominal_try=_d(raw.get("legal_share_nominal_try")),
        legal_share_piece_count=_d(raw.get("legal_share_piece_count")),
        free_float_ratio=_ratio(raw.get("free_float_ratio"), "free_float_ratio"),
        effective_free_float_ratio=_ratio(raw.get("effective_free_float_ratio"), "effective_free_float_ratio"),
        controlling_group_ratio=_ratio(raw.get("controlling_group_ratio"), "controlling_group_ratio"),
        treasury_valuation_units=_d(raw.get("treasury_valuation_units", "0")) or Decimal("0"),
        diluted_valuation_units=_d(raw.get("diluted_valuation_units")),
        privileged_share_flag=raw.get("privileged_share_flag"),
        price_try=_d(raw.get("price_try")),
        price_date=_iso_date(raw["price_date"]) if raw.get("price_date") else None,
        price_published_at=_iso_dt(raw.get("price_published_at")),
        ownership_source=str(raw.get("ownership_source", "KAP/MKK")),
        ownership_source_ref=raw.get("ownership_source_ref"),
        market_source=str(raw.get("market_source", "CANONICAL_MARKET")),
        market_source_ref=raw.get("market_source_ref"),
        schema_version=str(raw.get("schema_version", "fin-prod-002-v1")),
    )
    obj.validate()
    return obj


def load_market_ownership_input(path: str | Path) -> CanonicalMarketOwnershipInput:
    return from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def save_market_ownership_input(value: CanonicalMarketOwnershipInput, path: str | Path) -> None:
    def s(v):
        if isinstance(v, Decimal):
            return str(v)
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v
    raw = {k: s(v) for k, v in asdict(value).items()}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
