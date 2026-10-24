from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from statistics import median
from typing import Iterable, Mapping

from ..analysis.fundamental_analysis import calculate_ratios
from ..data.fundamental_data import (
    FundamentalFreshnessPolicy,
    evaluate_fundamental_freshness,
)
from ..models.fundamental_models import FinancialPeriod


class SectorReferenceError(ValueError):
    """Sektör referansı okuma veya karşılaştırma hatası."""


@dataclass(frozen=True)
class SectorReference:
    symbol: str
    sector: str
    market_cap: Decimal | None = None

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        sector = self.sector.strip()

        if not symbol:
            raise SectorReferenceError("Şirket sembolü boş olamaz.")
        if not sector:
            raise SectorReferenceError("Sektör adı boş olamaz.")

        market_cap = self.market_cap
        if market_cap is not None:
            try:
                market_cap = Decimal(str(market_cap))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise SectorReferenceError(
                    "Piyasa değeri sayısal olmalıdır."
                ) from exc
            if not market_cap.is_finite() or market_cap <= 0:
                raise SectorReferenceError(
                    "Piyasa değeri sıfırdan büyük olmalıdır."
                )

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "sector", sector)
        object.__setattr__(self, "market_cap", market_cap)


@dataclass(frozen=True)
class CompanyRatioReference:
    symbol: str
    sector: str
    period_key: str
    period_end: date
    currency: str
    price_to_earnings: Decimal | None
    price_to_book: Decimal | None
    current_ratio: Decimal | None
    debt_to_equity: Decimal | None
    roe: Decimal | None
    net_margin: Decimal | None
    free_cash_flow_margin: Decimal | None


@dataclass(frozen=True)
class RatioMedianComparison:
    metric: str
    company_value: Decimal | None
    sector_median: Decimal | None
    position: str


@dataclass(frozen=True)
class SectorComparison:
    symbol: str
    sector: str
    period_key: str
    period_end: date
    peer_count: int
    comparisons: tuple[RatioMedianComparison, ...]


REFERENCE_COLUMNS = ("symbol", "sector")
OPTIONAL_COLUMNS = ("market_cap",)


def references_from_csv_bytes(
    content: bytes,
) -> dict[str, SectorReference]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SectorReferenceError(
            "Sektör referans dosyası UTF-8 olmalıdır."
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = tuple(reader.fieldnames or ())
    missing = [
        column
        for column in REFERENCE_COLUMNS
        if column not in fieldnames
    ]
    if missing:
        raise SectorReferenceError(
            "Eksik sektör referans alanları: "
            + ", ".join(missing)
        )

    references: dict[str, SectorReference] = {}
    for line_number, row in enumerate(reader, start=2):
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            raise SectorReferenceError(
                f"{line_number}. satırda şirket sembolü boş."
            )
        if symbol in references:
            raise SectorReferenceError(
                f"Tekrarlanan şirket sembolü: {symbol}"
            )

        market_cap_raw = str(row.get("market_cap", "")).strip()
        references[symbol] = SectorReference(
            symbol=symbol,
            sector=str(row.get("sector", "")),
            market_cap=(
                Decimal(market_cap_raw)
                if market_cap_raw
                else None
            ),
        )

    if not references:
        raise SectorReferenceError(
            "Sektör referans dosyasında kayıt bulunamadı."
        )

    return references


def _valuation_ratio(
    market_cap: Decimal | None,
    denominator: Decimal,
) -> Decimal | None:
    if market_cap is None or denominator <= 0:
        return None
    return (market_cap / denominator).quantize(
        Decimal("0.01")
    )


def build_company_ratio_references(
    periods: Iterable[FinancialPeriod],
    references: Mapping[str, SectorReference],
    *,
    today: date | None = None,
    freshness_policy: FundamentalFreshnessPolicy | None = None,
) -> tuple[CompanyRatioReference, ...]:
    grouped: dict[str, list[FinancialPeriod]] = {}
    for period in periods:
        grouped.setdefault(period.symbol, []).append(period)

    reference_day = today or date.today()
    policy = freshness_policy or FundamentalFreshnessPolicy()
    results: list[CompanyRatioReference] = []

    for symbol, company_periods in grouped.items():
        reference = references.get(symbol)
        if reference is None:
            continue

        freshness = evaluate_fundamental_freshness(
            company_periods,
            today=reference_day,
            policy=policy,
        )
        if freshness.locked:
            continue

        latest = max(
            company_periods,
            key=lambda item: (
                item.period_end,
                item.fiscal_year,
                item.fiscal_quarter,
            ),
        )
        ratios = calculate_ratios(latest)

        results.append(
            CompanyRatioReference(
                symbol=symbol,
                sector=reference.sector,
                period_key=latest.period_key,
                period_end=latest.period_end,
                currency=latest.currency,
                price_to_earnings=_valuation_ratio(
                    reference.market_cap,
                    latest.net_income,
                ),
                price_to_book=_valuation_ratio(
                    reference.market_cap,
                    latest.total_equity,
                ),
                current_ratio=ratios.current_ratio,
                debt_to_equity=ratios.debt_to_equity,
                roe=ratios.roe,
                net_margin=ratios.net_margin,
                free_cash_flow_margin=(
                    ratios.free_cash_flow_margin
                ),
            )
        )

    return tuple(
        sorted(
            results,
            key=lambda item: (
                item.sector,
                item.period_end,
                item.symbol,
            ),
        )
    )


def _median_decimal(
    values: Iterable[Decimal | None],
) -> Decimal | None:
    available = [value for value in values if value is not None]
    if not available:
        return None
    return Decimal(str(median(available))).quantize(
        Decimal("0.01")
    )


def _position(
    company_value: Decimal | None,
    sector_median: Decimal | None,
) -> str:
    if company_value is None or sector_median is None:
        return "Veri yok"
    if company_value > sector_median:
        return "Sektör medyanının üzerinde"
    if company_value < sector_median:
        return "Sektör medyanının altında"
    return "Sektör medyanına eşit"


def compare_company_to_sector(
    records: Iterable[CompanyRatioReference],
    symbol: str,
) -> SectorComparison:
    normalized_symbol = symbol.strip().upper()
    records_tuple = tuple(records)
    company = next(
        (
            record
            for record in records_tuple
            if record.symbol == normalized_symbol
        ),
        None,
    )
    if company is None:
        raise SectorReferenceError(
            "Şirket için güncel sektör referansı bulunamadı."
        )

    peers = tuple(
        record
        for record in records_tuple
        if record.sector == company.sector
        and record.period_end == company.period_end
        and record.currency == company.currency
    )
    if len(peers) < 2:
        raise SectorReferenceError(
            "Sektör karşılaştırması için aynı dönem ve para "
            "biriminde en az iki şirket gerekir."
        )

    metric_fields = (
        ("F/K", "price_to_earnings"),
        ("PD/DD", "price_to_book"),
        ("Cari oran", "current_ratio"),
        ("Borç / özsermaye", "debt_to_equity"),
        ("ROE (%)", "roe"),
        ("Net kâr marjı (%)", "net_margin"),
        (
            "Serbest nakit akışı marjı (%)",
            "free_cash_flow_margin",
        ),
    )

    comparisons = []
    for metric, field_name in metric_fields:
        company_value = getattr(company, field_name)
        sector_median = _median_decimal(
            getattr(peer, field_name) for peer in peers
        )
        comparisons.append(
            RatioMedianComparison(
                metric=metric,
                company_value=company_value,
                sector_median=sector_median,
                position=_position(
                    company_value,
                    sector_median,
                ),
            )
        )

    return SectorComparison(
        symbol=company.symbol,
        sector=company.sector,
        period_key=company.period_key,
        period_end=company.period_end,
        peer_count=len(peers),
        comparisons=tuple(comparisons),
    )


def sector_comparison_rows(
    comparison: SectorComparison,
) -> list[dict[str, object]]:
    return [
        {
            "Finansal oran": item.metric,
            "Şirket": item.company_value,
            "Sektör medyanı": item.sector_median,
            "Konum": item.position,
        }
        for item in comparison.comparisons
    ]
