from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class FinancialReportIdentity:
    symbol: str
    company_name: str
    disclosure_id: str | None
    fiscal_year: int
    fiscal_period: int
    report_date: date
    published_at: datetime | None
    consolidation_scope: str
    currency: str
    currency_scale: Decimal
    source: str = "KAP"


@dataclass(frozen=True)
class CanonicalFinancialFact:
    statement: str
    metric_code: str | None
    source_label: str
    period_label: str
    value: Decimal
    note_ref: str | None = None


@dataclass(frozen=True)
class KapFinancialImportResult:
    identity: FinancialReportIdentity
    facts: tuple[CanonicalFinancialFact, ...]
    unmapped_labels: tuple[str, ...]
    source_sha256: str
    parser_version: str = "fin001-v1"

    def current_values(self) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for fact in self.facts:
            if fact.metric_code and fact.period_label.startswith("Cari Dönem"):
                result.setdefault(fact.metric_code, fact.value)
        return result
