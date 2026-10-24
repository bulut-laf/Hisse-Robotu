from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping

FUND_SCHEMA_VERSION = "fund-data-contract-v1"


class DataQualityState(str, Enum):
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    INVALID = "INVALID"
    UNAVAILABLE = "UNAVAILABLE"


class FreshnessState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


def _utc(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} timezone-aware olmalıdır.")


def _fund_id(value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError("canonical_fund_id bo? olamaz.")

    prefix = "fund:tefas:"
    if normalized.startswith(prefix):
        fund_code = normalized[len(prefix):].strip()
        if fund_code.isdigit():
            raise ValueError(
                f"INVALID_NUMERIC_TEFAS_FUND_ID:{normalized}"
            )

    return normalized

@dataclass(frozen=True, slots=True)
class FundIdentity:
    fund_code: str
    fund_name: str
    canonical_fund_id: str
    category_id: str | None
    category_name: str | None
    provider: str
    provider_fund_id: str
    currency: str
    is_active: bool
    as_of_date: date

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_fund_id", _fund_id(self.canonical_fund_id))
        if not self.fund_code or not self.provider or not self.provider_fund_id:
            raise ValueError("Fon kodu ve sağlayıcı kimliği zorunludur.")


@dataclass(frozen=True, slots=True)
class FundDailyObservation:
    canonical_fund_id: str
    observation_date: date
    unit_price: Decimal | None
    fund_size: Decimal | None
    investor_count: int | None
    shares_outstanding: Decimal | None
    daily_return: Decimal | None
    provider: str
    fetched_at: datetime
    source_as_of: datetime
    data_quality_state: DataQualityState
    category_rank: int | None = None
    category_fund_count: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_fund_id", _fund_id(self.canonical_fund_id))
        _utc(self.fetched_at, "fetched_at")
        _utc(self.source_as_of, "source_as_of")
        if self.observation_date > datetime.now(timezone.utc).date():
            raise ValueError("leri tarihli fon gözlemi kabul edilmez.")


@dataclass(frozen=True, slots=True)
class FundPortfolioObservation:
    canonical_fund_id: str
    observation_date: date
    asset_allocation: Mapping[str, Decimal] | None
    major_holdings: tuple[str, ...] | None
    cash_ratio: Decimal | None
    equity_ratio: Decimal | None
    fixed_income_ratio: Decimal | None
    foreign_asset_ratio: Decimal | None
    precious_metal_ratio: Decimal | None
    other_ratio: Decimal | None
    provider: str
    fetched_at: datetime
    data_quality_state: DataQualityState

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_fund_id", _fund_id(self.canonical_fund_id))
        _utc(self.fetched_at, "fetched_at")


@dataclass(frozen=True, slots=True)
class FundCostAndMetadata:
    canonical_fund_id: str
    management_fee: Decimal | None
    total_expense_ratio: Decimal | None
    risk_value: str | None
    benchmark: str | None
    inception_date: date | None
    settlement_terms: str | None
    minimum_transaction_amount: Decimal | None
    umbrella_fund: str | None
    founder: str | None
    manager: str | None
    tax_metadata: str | None
    provider: str
    source_as_of: datetime
    data_quality_state: DataQualityState

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_fund_id", _fund_id(self.canonical_fund_id))
        _utc(self.source_as_of, "source_as_of")


@dataclass(frozen=True, slots=True)
class FundCategoryMembership:
    canonical_fund_id: str
    category_id: str | None
    category_name: str | None
    provider_category_label: str | None
    effective_from: date
    effective_to: date | None
    provider: str
    source_as_of: datetime
    mapping_state: str = "MAPPED"

    def __post_init__(self) -> None:
        object.__setattr__(self, "canonical_fund_id", _fund_id(self.canonical_fund_id))
        _utc(self.source_as_of, "source_as_of")
        if self.category_id is None and self.mapping_state != "UNMAPPED":
            raise ValueError("Kategori kimliği yoksa mapping_state UNMAPPED olmalıdır.")


FundRecord = FundIdentity | FundDailyObservation | FundPortfolioObservation | FundCostAndMetadata | FundCategoryMembership


@dataclass(frozen=True, slots=True)
class FundDataEnvelope:
    provider: str
    requested_at: datetime
    fetched_at: datetime
    source_as_of: datetime
    records: tuple[FundRecord, ...]
    warnings: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    completeness: Decimal = Decimal("1")
    freshness_state: FreshnessState = FreshnessState.UNKNOWN
    provenance: Mapping[str, str] | None = None
    schema_version: str = FUND_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("requested_at", "fetched_at", "source_as_of"):
            _utc(getattr(self, name), name)
        if self.schema_version != FUND_SCHEMA_VERSION:
            raise ValueError("Desteklenmeyen fon veri sözleşmesi sürümü.")
        if not Decimal("0") <= self.completeness <= Decimal("1"):
            raise ValueError("completeness 0-1 aralığında olmalıdır.")


def to_primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value):
        payload = {f.name: to_primitive(getattr(value, f.name)) for f in fields(value)}
        payload["record_type"] = type(value).__name__
        return payload
    if isinstance(value, Mapping):
        return {str(k): to_primitive(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [to_primitive(item) for item in value]
    return value
