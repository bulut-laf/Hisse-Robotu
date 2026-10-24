from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from app.analysis.financial_intelligence_bank_daily_production_bridge import (
    BankDailyProductionContext,
    build_bank_daily_production_context,
)
from app.analysis.financial_intelligence_panel_read_model import (
    build_financial_intelligence_panel,
)


@dataclass(frozen=True)
class FinancialIntelligenceDailyContext:
    symbol: str
    panel: Mapping[str, Any]
    bank: BankDailyProductionContext | None


def _attach_bank_production_section(
    panel: Mapping[str, Any],
    bank: BankDailyProductionContext | None,
) -> dict[str, Any]:
    panel_copy = deepcopy(dict(panel))

    if bank is None:
        return panel_copy

    sections = dict(
        panel_copy.get("sections") or {}
    )

    sections["bank_production"] = {
        "status": "ACTIVE",
        "symbol": bank.symbol,
        "as_of": bank.as_of,
        "publication_date": bank.publication_date,
        "source_type": bank.source_type,
        "canonical_input_ready": bank.canonical_input_ready,
        "scoring_ready": bank.scoring_ready,
        "production_evidence": bank.production_evidence,
        "activation_ready": bank.activation_ready,
        "read_only": True,
    }

    panel_copy["sections"] = sections

    return panel_copy


def build_financial_intelligence_daily_context(
    root: Any,
    symbol: str,
    *,
    period_key: str | None = None,
    bank_record: Mapping[str, Any] | None = None,
) -> FinancialIntelligenceDailyContext:
    """
    Read-only Financial Intelligence daily context.

    Existing FI panel remains the primary read model.

    A BANK production section is attached only when:
    - an explicit BANK source record is supplied,
    - its symbol matches the requested symbol,
    - the existing BANK production bridge accepts it.

    No source discovery, persistence, scheduling or trading-side
    mutation is performed.
    """

    normalized_symbol = str(symbol).strip().upper()

    if period_key is None:
        panel = build_financial_intelligence_panel(
            root,
            normalized_symbol,
        )
    else:
        panel = build_financial_intelligence_panel(
            root,
            normalized_symbol,
            period_key=period_key,
        )

    bank_context = None

    if bank_record is not None:
        record_symbol = str(
            bank_record.get("symbol", "")
        ).strip().upper()

        if record_symbol == normalized_symbol:
            bank_context = (
                build_bank_daily_production_context(
                    bank_record
                )
            )

    visible_panel = _attach_bank_production_section(
        panel,
        bank_context,
    )

    return FinancialIntelligenceDailyContext(
        symbol=normalized_symbol,
        panel=visible_panel,
        bank=bank_context,
    )