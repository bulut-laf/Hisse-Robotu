from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from ..models.fundamental_models import FinancialPeriod
from .fundamental_data import (
    FundamentalDataError,
    periods_from_records,
)


class KapFundamentalError(RuntimeError):
    """KAP finansal veri entegrasyonunun ortak hata türü."""


class KapFundamentalSourceError(KapFundamentalError):
    """KAP finansal veri kaynağına erişilemediğinde oluşur."""


class KapFundamentalParseError(KapFundamentalError):
    """KAP finansal veri paketi güvenle ayrıştırılamadığında oluşur."""


FundamentalFetcher = Callable[
    [str, date | None, date | None],
    Iterable[Mapping[str, Any]],
]


@dataclass(frozen=True)
class KapFundamentalSourceStatus:
    symbol: str
    source: str
    fetched_at: datetime
    record_count: int
    accepted_count: int
    rejected_count: int
    data_identity: str
    locked: bool
    explanation: str


@dataclass(frozen=True)
class KapFundamentalPackage:
    periods: tuple[FinancialPeriod, ...]
    status: KapFundamentalSourceStatus
    rejected_records: tuple[str, ...]


_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "symbol": ("symbol", "ticker", "stockCode", "companyCode"),
    "period_end": (
        "period_end",
        "periodEnd",
        "reportDate",
        "accountingPeriodEnd",
    ),
    "fiscal_year": ("fiscal_year", "fiscalYear", "year"),
    "fiscal_quarter": (
        "fiscal_quarter",
        "fiscalQuarter",
        "quarter",
    ),
    "currency": ("currency", "currencyCode"),
    "revenue": ("revenue", "sales", "netSales"),
    "gross_profit": ("gross_profit", "grossProfit"),
    "operating_profit": (
        "operating_profit",
        "operatingProfit",
        "operatingIncome",
    ),
    "ebitda": ("ebitda", "favok", "EBITDA"),
    "net_income": ("net_income", "netIncome", "netProfit"),
    "total_assets": ("total_assets", "totalAssets"),
    "total_equity": ("total_equity", "totalEquity", "equity"),
    "total_debt": ("total_debt", "totalDebt"),
    "cash_and_equivalents": (
        "cash_and_equivalents",
        "cashAndEquivalents",
        "cash",
    ),
    "current_assets": ("current_assets", "currentAssets"),
    "current_liabilities": (
        "current_liabilities",
        "currentLiabilities",
    ),
    "operating_cash_flow": (
        "operating_cash_flow",
        "operatingCashFlow",
        "cashFlowFromOperations",
    ),
    "capital_expenditure": (
        "capital_expenditure",
        "capitalExpenditure",
        "capex",
    ),
    "shares_outstanding": (
        "shares_outstanding",
        "sharesOutstanding",
    ),
    "source": ("source", "sourceName"),
    "published_at": (
        "published_at",
        "publishedAt",
        "disclosureDate",
    ),
}


def _first_value(
    record: Mapping[str, Any],
    aliases: tuple[str, ...],
) -> Any:
    for alias in aliases:
        if alias in record and record[alias] not in (None, ""):
            return record[alias]
    return None


def normalize_kap_record(
    record: Mapping[str, Any],
    *,
    requested_symbol: str,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for target, aliases in _FIELD_ALIASES.items():
        value = _first_value(record, aliases)
        if value is not None:
            normalized[target] = value

    normalized.setdefault("symbol", requested_symbol)
    normalized.setdefault("source", "KAP")

    if str(normalized["symbol"]).strip().upper() != (
        requested_symbol.strip().upper()
    ):
        raise KapFundamentalParseError(
            "KAP kaydındaki şirket kodu istenen sembolle eşleşmiyor."
        )

    if "period_end" not in normalized:
        raise KapFundamentalParseError(
            "KAP kaydında finansal dönem sonu bulunamadı."
        )

    period_end = date.fromisoformat(
        str(normalized["period_end"])[:10]
    )
    normalized.setdefault("fiscal_year", period_end.year)

    if "fiscal_quarter" not in normalized:
        normalized["fiscal_quarter"] = {
            3: 1,
            6: 2,
            9: 3,
            12: 4,
        }.get(period_end.month)
        if normalized["fiscal_quarter"] is None:
            raise KapFundamentalParseError(
                "KAP kaydının mali çeyreği dönem sonundan çıkarılamadı."
            )

    normalized.setdefault("currency", "TRY")
    return normalized


def _package_identity(
    periods: Iterable[FinancialPeriod],
) -> str:
    records = [
        {
            "symbol": item.symbol,
            "period_key": item.period_key,
            "period_end": item.period_end.isoformat(),
            "currency": item.currency,
            "source": item.source,
            "published_at": (
                item.published_at.isoformat()
                if item.published_at is not None
                else ""
            ),
        }
        for item in sorted(
            periods,
            key=lambda value: (
                value.symbol,
                value.period_end,
                value.fiscal_quarter,
            ),
        )
    ]
    raw = json.dumps(
        records,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class KapFundamentalClient:
    """Yapılandırılmış KAP finansal kayıtlarını standart modele dönüştürür."""

    def __init__(
        self,
        *,
        fetcher: FundamentalFetcher,
        source_name: str = "KAP",
    ) -> None:
        self._fetcher = fetcher
        self._source_name = source_name.strip() or "KAP"

    def fetch(
        self,
        symbol: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> KapFundamentalPackage:
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("Şirket sembolü boş olamaz.")

        try:
            raw_records = list(
                self._fetcher(
                    normalized_symbol,
                    start_date,
                    end_date,
                )
            )
        except Exception as exc:
            raise KapFundamentalSourceError(
                f"{normalized_symbol} KAP finansal verisi alınamadı: {exc}"
            ) from exc

        accepted_records: list[dict[str, Any]] = []
        rejected: list[str] = []

        for index, record in enumerate(raw_records, start=1):
            try:
                accepted_records.append(
                    normalize_kap_record(
                        record,
                        requested_symbol=normalized_symbol,
                    )
                )
            except (
                ValueError,
                TypeError,
                KapFundamentalParseError,
            ) as exc:
                rejected.append(f"Kayıt {index}: {exc}")

        try:
            periods = periods_from_records(accepted_records)
        except FundamentalDataError as exc:
            raise KapFundamentalParseError(str(exc)) from exc

        fetched_at = datetime.now().astimezone()
        if not periods:
            status = KapFundamentalSourceStatus(
                symbol=normalized_symbol,
                source=self._source_name,
                fetched_at=fetched_at,
                record_count=len(raw_records),
                accepted_count=0,
                rejected_count=len(rejected),
                data_identity="",
                locked=True,
                explanation=(
                    "Doğrulanabilir KAP finansal dönemi bulunmadı; "
                    "temel analiz kilitlendi."
                ),
            )
            return KapFundamentalPackage(
                periods=(),
                status=status,
                rejected_records=tuple(rejected),
            )

        identity = _package_identity(periods)
        status = KapFundamentalSourceStatus(
            symbol=normalized_symbol,
            source=self._source_name,
            fetched_at=fetched_at,
            record_count=len(raw_records),
            accepted_count=len(periods),
            rejected_count=len(rejected),
            data_identity=identity,
            locked=False,
            explanation=(
                f"{len(periods)} finansal dönem KAP kaynağından "
                "doğrulandı."
            ),
        )
        return KapFundamentalPackage(
            periods=tuple(periods),
            status=status,
            rejected_records=tuple(rejected),
        )
