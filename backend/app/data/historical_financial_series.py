from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

from ..models.financial_intelligence_models import KapFinancialImportResult


class HistoricalFinancialSeriesError(ValueError):
    """Historical series cannot be built without violating canonical rules."""


_DATE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})")


@dataclass(frozen=True)
class FinancialPeriod:
    kind: str  # INSTANT | DURATION
    start_date: date | None
    end_date: date
    comparison_role: str
    source_period_label: str


@dataclass(frozen=True)
class HistoricalFinancialPoint:
    symbol: str
    metric_code: str
    statement: str
    source_label: str
    value: Decimal
    period_kind: str
    period_start: date | None
    period_end: date
    comparison_role: str
    published_at: datetime | None
    consolidation_scope: str
    currency: str
    currency_scale: Decimal
    disclosure_id: str | None
    source_sha256: str
    note_ref: str | None = None

    @property
    def canonical_key(self) -> tuple:
        return (
            self.symbol,
            self.metric_code,
            self.period_kind,
            self.period_start,
            self.period_end,
            self.consolidation_scope,
            self.currency,
            self.currency_scale,
        )


@dataclass(frozen=True)
class HistoricalFinancialSeries:
    symbol: str
    consolidation_scope: str
    currency: str
    currency_scale: Decimal
    points: tuple[HistoricalFinancialPoint, ...]
    warnings: tuple[str, ...] = ()
    series_version: str = "fin002-v1"

    def _resolved_points(self, as_of: datetime | None = None) -> tuple[HistoricalFinancialPoint, ...]:
        candidates = [
            p for p in self.points
            if as_of is None or p.published_at is None or p.published_at <= as_of
        ]
        by_key: dict[tuple, HistoricalFinancialPoint] = {}
        for point in candidates:
            existing = by_key.get(point.canonical_key)
            if existing is None:
                by_key[point.canonical_key] = point
                continue
            existing_pub = existing.published_at or datetime.min
            point_pub = point.published_at or datetime.min
            if point_pub >= existing_pub:
                by_key[point.canonical_key] = point
        return tuple(by_key.values())

    def available_as_of(self, as_of: datetime) -> "HistoricalFinancialSeries":
        return HistoricalFinancialSeries(
            symbol=self.symbol,
            consolidation_scope=self.consolidation_scope,
            currency=self.currency,
            currency_scale=self.currency_scale,
            points=self._resolved_points(as_of),
            warnings=self.warnings,
            series_version=self.series_version,
        )

    def metric_series(
        self,
        metric_code: str,
        *,
        period_kind: str | None = None,
        as_of: datetime | None = None,
    ) -> tuple[HistoricalFinancialPoint, ...]:
        source = self._resolved_points(as_of)
        selected = [
            p for p in source
            if p.metric_code == metric_code
            and (period_kind is None or p.period_kind == period_kind)
        ]
        selected.sort(key=lambda p: (p.period_end, p.period_start or p.period_end, p.published_at or datetime.min))
        return tuple(selected)

    def latest_value(
        self,
        metric_code: str,
        *,
        period_kind: str | None = None,
        as_of: datetime | None = None,
    ) -> HistoricalFinancialPoint | None:
        series = self.metric_series(metric_code, period_kind=period_kind, as_of=as_of)
        return series[-1] if series else None


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%d.%m.%Y").date()


def parse_period_label(label: str) -> FinancialPeriod:
    dates = [_parse_date(x) for x in _DATE_RE.findall(label)]
    if not dates:
        raise HistoricalFinancialSeriesError(f"Period label has no date: {label!r}")

    normalized = re.sub(r"\s+", " ", label).strip().casefold()
    is_current = normalized.startswith("cari dönem".casefold())
    is_previous = normalized.startswith("önceki dönem".casefold())
    is_three_month = "3 aylık" in normalized

    if len(dates) == 1:
        role = "CURRENT_INSTANT" if is_current else "PRIOR_INSTANT" if is_previous else "INSTANT"
        return FinancialPeriod(
            kind="INSTANT",
            start_date=None,
            end_date=dates[0],
            comparison_role=role,
            source_period_label=label,
        )

    if len(dates) >= 2:
        start, end = dates[0], dates[1]
        if end < start:
            raise HistoricalFinancialSeriesError(f"Period end before start: {label!r}")
        if is_current and is_three_month:
            role = "CURRENT_QUARTER"
        elif is_previous and is_three_month:
            role = "PRIOR_YEAR_QUARTER"
        elif is_current:
            role = "CURRENT_YTD"
        elif is_previous:
            role = "PRIOR_YEAR_SAME_PERIOD"
        else:
            role = "DURATION"
        return FinancialPeriod(
            kind="DURATION",
            start_date=start,
            end_date=end,
            comparison_role=role,
            source_period_label=label,
        )

    raise HistoricalFinancialSeriesError(f"Unsupported period label: {label!r}")


def _validate_import_group(imports: tuple[KapFinancialImportResult, ...]) -> tuple[str, str, str, Decimal]:
    if not imports:
        raise HistoricalFinancialSeriesError("At least one KAP financial import is required.")

    symbols = {x.identity.symbol for x in imports}
    scopes = {x.identity.consolidation_scope for x in imports}
    currencies = {x.identity.currency for x in imports}
    scales = {x.identity.currency_scale for x in imports}

    if len(symbols) != 1:
        raise HistoricalFinancialSeriesError(f"Mixed symbols are not allowed: {sorted(symbols)}")
    if len(scopes) != 1:
        raise HistoricalFinancialSeriesError(f"Mixed consolidation scopes are not allowed: {sorted(scopes)}")
    if len(currencies) != 1:
        raise HistoricalFinancialSeriesError(f"Mixed currencies are not allowed: {sorted(currencies)}")
    if len(scales) != 1:
        raise HistoricalFinancialSeriesError(f"Mixed currency scales are not allowed: {sorted(str(x) for x in scales)}")

    return next(iter(symbols)), next(iter(scopes)), next(iter(currencies)), next(iter(scales))


def build_historical_financial_series(
    imports: Iterable[KapFinancialImportResult],
) -> HistoricalFinancialSeries:
    imported = tuple(imports)
    symbol, scope, currency, scale = _validate_import_group(imported)

    warnings: set[str] = set()
    points_all: list[HistoricalFinancialPoint] = []
    latest_by_key: dict[tuple, HistoricalFinancialPoint] = {}

    for report in imported:
        for fact in report.facts:
            if not fact.metric_code:
                continue
            # FIN-001 label mapping is intentionally broad. FIN-002 must not
            # reinterpret OCI/equity-change labels as core P&L/balance/cash metrics.
            if fact.statement not in {"BALANCE_SHEET", "INCOME_STATEMENT", "CASH_FLOW"}:
                continue
            try:
                period = parse_period_label(fact.period_label)
            except HistoricalFinancialSeriesError:
                warnings.add(f"UNPARSED_PERIOD_LABEL:{fact.period_label}")
                continue

            point = HistoricalFinancialPoint(
                symbol=symbol,
                metric_code=fact.metric_code,
                statement=fact.statement,
                source_label=fact.source_label,
                value=fact.value,
                period_kind=period.kind,
                period_start=period.start_date,
                period_end=period.end_date,
                comparison_role=period.comparison_role,
                published_at=report.identity.published_at,
                consolidation_scope=scope,
                currency=currency,
                currency_scale=scale,
                disclosure_id=report.identity.disclosure_id,
                source_sha256=report.source_sha256,
                note_ref=fact.note_ref,
            )

            existing = latest_by_key.get(point.canonical_key)
            if existing is not None and existing.value != point.value:
                warnings.add(
                    "REVISED_VALUE:"
                    f"{point.metric_code}:{point.period_end.isoformat()}:"
                    f"{existing.value}->{point.value}"
                )
            existing_pub = existing.published_at if existing and existing.published_at else datetime.min
            point_pub = point.published_at or datetime.min
            if existing is None or point_pub >= existing_pub:
                latest_by_key[point.canonical_key] = point

            points_all.append(point)

    # Preserve every disclosed version for point-in-time replay. Read methods
    # resolve the latest version that was actually available at the requested time.
    points = tuple(sorted(
        points_all,
        key=lambda p: (
            p.metric_code,
            p.period_end,
            p.period_start or p.period_end,
            p.published_at or datetime.min,
            p.disclosure_id or "",
        ),
    ))

    if not points:
        raise HistoricalFinancialSeriesError("No mapped canonical facts could be normalized into a historical series.")

    return HistoricalFinancialSeries(
        symbol=symbol,
        consolidation_scope=scope,
        currency=currency,
        currency_scale=scale,
        points=points,
        warnings=tuple(sorted(warnings)),
    )
