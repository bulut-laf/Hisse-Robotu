from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class FundEtfContext:
    report_type: str = "fund_etf_commentary"
    equity_etfs: list[str] = field(default_factory=list)
    sector_etfs: list[str] = field(default_factory=list)
    commodity_funds: list[str] = field(default_factory=list)
    fund_notes: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_type": self.report_type,
            "equity_etfs": list(self.equity_etfs),
            "sector_etfs": list(self.sector_etfs),
            "commodity_funds": list(self.commodity_funds),
            "fund_notes": list(self.fund_notes),
            "risk_notes": list(self.risk_notes),
        }
