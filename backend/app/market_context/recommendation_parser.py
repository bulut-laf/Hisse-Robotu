from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedRecommendation:
    buy: list[str] = field(default_factory=list)
    sell: list[str] = field(default_factory=list)
    watch: list[str] = field(default_factory=list)
    target_prices: dict[str, str] = field(default_factory=dict)
    time_horizon: str | None = None


class RecommendationParser:
    """Kurum önerilerini karar vermeden yapılandırır."""

    def parse(self, text: str) -> ParsedRecommendation:
        result = ParsedRecommendation()

        section = None
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue

            upper = line.upper()

            if upper.startswith("AL"):
                section = "buy"
                continue
            if upper.startswith("SAT"):
                section = "sell"
                continue
            if upper.startswith("İZLE") or upper.startswith("IZLE"):
                section = "watch"
                continue

            symbol = self._symbol(line)
            if symbol and section:
                getattr(result, section).append(symbol)

            self._target_price(result, line)

            if "hafta" in line.lower():
                result.time_horizon = "weekly"
            elif "gün" in line.lower():
                result.time_horizon = "daily"

        return result

    @staticmethod
    def _symbol(line: str) -> str | None:
        match = re.fullmatch(r"[A-ZÇĞİÖŞÜ]{4,6}", line)
        return match.group(0) if match else None

    @staticmethod
    def _target_price(result: ParsedRecommendation, line: str) -> None:
        match = re.search(
            r"([A-ZÇĞİÖŞÜ]{4,6})\s+(\d+(?:[.,]\d+)?)",
            line,
        )
        if match:
            result.target_prices[match.group(1)] = match.group(2)
