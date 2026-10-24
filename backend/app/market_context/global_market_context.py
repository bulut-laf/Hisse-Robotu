from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class GlobalMarketContext:
    report_type: str = "global_market_commentary"
    us_market: str | None = None
    europe_market: str | None = None
    asia_market: str | None = None
    macro_topics: list[str] = field(default_factory=list)
    currencies: list[str] = field(default_factory=list)
    commodities: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_type": self.report_type,
            "regions": {
                "us_market": self.us_market,
                "europe_market": self.europe_market,
                "asia_market": self.asia_market,
            },
            "macro_topics": self.macro_topics,
            "currencies": self.currencies,
            "commodities": self.commodities,
            "risk_notes": self.risk_notes,
        }
