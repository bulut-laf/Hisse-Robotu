from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.analysis.financial_intelligence_bank_production_source_onboarding import (
    evaluate_bank_production_source,
)


@dataclass(frozen=True)
class BankDailyProductionContext:
    symbol: str
    as_of: str
    publication_date: str
    source_type: str
    source_uri: str
    canonical_input_ready: bool
    scoring_ready: bool
    production_evidence: bool
    activation_ready: bool


def build_bank_daily_production_context(
    record: Mapping[str, Any],
) -> BankDailyProductionContext | None:
    result = evaluate_bank_production_source(record)

    if result.status != "PASS":
        return None

    if result.blocker is not None:
        return None

    if not result.canonical_input_ready:
        return None

    if not result.scoring_ready:
        return None

    if not result.production_evidence:
        return None

    if not result.activation_ready:
        return None

    return BankDailyProductionContext(
        symbol=result.symbol,
        as_of=result.as_of,
        publication_date=result.publication_date,
        source_type=result.source_type,
        source_uri=result.source_uri,
        canonical_input_ready=result.canonical_input_ready,
        scoring_ready=result.scoring_ready,
        production_evidence=result.production_evidence,
        activation_ready=result.activation_ready,
    )