from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedMarketContext:
    index_outlook: str | None = None
    supports: list[str] = field(default_factory=list)
    resistances: list[str] = field(default_factory=list)
    external_market_outlook: str | None = None
    futures_outlook: str | None = None
    macro_risks: list[str] = field(default_factory=list)
    sector_impacts: list[dict[str, str]] = field(default_factory=list)
    stock_news: list[dict[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class MarketContextParser:
    POSITIVE_TERMS = ("pozitif", "olumlu", "artıda", "güçlü")
    NEGATIVE_TERMS = ("negatif", "olumsuz", "ekside", "zayıf")
    CAUTIOUS_TERMS = ("temkinli", "karışık", "yatay", "dalgalı")

    LEVEL_PATTERN = r"\d{1,3}(?:\.\d{3})?(?:–\d{1,3}(?:\.\d{3})?)?"

    def parse(self, text: str) -> ParsedMarketContext:
        normalized = text.replace("\r", "")
        sentences = self._sentences(normalized)

        return ParsedMarketContext(
            index_outlook=self._extract_index_outlook(sentences),
            supports=self._extract_supports(normalized),
            resistances=self._extract_resistances(normalized),
            external_market_outlook=self._extract_external(sentences),
            futures_outlook=self._extract_futures(sentences),
            macro_risks=self._extract_macro(sentences),
            sector_impacts=self._extract_sector_impacts(sentences),
            stock_news=self._extract_stock_news(sentences),
        )

    @staticmethod
    def _sentences(text: str):
        return [
            x.strip()
            for x in re.split(r"(?<=[.!?])\s+|\n+", text)
            if x.strip()
        ]

    def _sentiment(self, text):
        t = text.casefold()
        if any(x in t for x in self.POSITIVE_TERMS) and any(
            x in t for x in self.CAUTIOUS_TERMS
        ):
            return "Temkinli / Pozitif"
        if any(x in t for x in self.POSITIVE_TERMS):
            return "Pozitif"
        if any(x in t for x in self.NEGATIVE_TERMS):
            return "Negatif"
        if any(x in t for x in self.CAUTIOUS_TERMS):
            return "Temkinli"
        return None

    def _extract_index_outlook(self, sentences):
        for s in sentences:
            if "bist100" in s.casefold() or "endeks" in s.casefold():
                result = self._sentiment(s)
                if result:
                    return result
        return None

    def _extract_supports(self, text):
        return self._extract_levels_near_keyword(text, "destek")

    def _extract_resistances(self, text):
        return self._extract_levels_near_keyword(text, "direnç")

    def _extract_levels_near_keyword(self, text, keyword):
        result = []
        for sentence in self._sentences(text):
            if keyword not in sentence.casefold():
                continue

            for value in re.findall(self.LEVEL_PATTERN, sentence):
                value = value.strip()
                if self._valid_level(value) and value not in result:
                    result.append(value)

        return result

    @staticmethod
    def _valid_level(value):
        digits = value.replace(".", "").replace("–", "")
        return digits.isdigit() and int(digits[:6]) > 1000

    def _extract_external(self, sentences):
        for s in sentences:
            if "asya" in s.casefold() or "abd vadeli" in s.casefold():
                return self._sentiment(s)
        return None

    def _extract_futures(self, sentences):
        for s in sentences:
            if "bist30 kontrat" in s.casefold():
                return self._sentiment(s)
        return None


    def _extract_sector_impacts(self, sentences):
        result: list[dict[str, str]] = []

        for sentence in sentences:
            match = re.match(
                r"^\s*([A-ZÇĞİÖŞÜa-zçğıöşü][A-ZÇĞİÖŞÜa-zçğıöşü0-9\s/&-]*?)\s+sektörü\b",
                sentence,
                flags=re.IGNORECASE,
            )
            if not match:
                continue

            sector = match.group(1).strip()
            item = {
                "sector": sector,
                "text": sentence,
            }

            sentiment = self._sentiment(sentence)
            if sentiment:
                item["sentiment"] = sentiment

            result.append(item)

        return result

    @staticmethod
    def _extract_stock_news(sentences):
        result: list[dict[str, str]] = []

        for sentence in sentences:
            # BIST sembolleri pratikte büyük harf/rakam biçimindedir.
            # Cümlenin başındaki sembolü korur; KAP ifadesi varsa haber olarak alır.
            match = re.match(r"^\s*([A-Z][A-Z0-9]{2,9})\b", sentence)
            if not match:
                continue

            symbol = match.group(1)
            lowered = sentence.casefold()

            if "kap" not in lowered and "açıklama" not in lowered and "haber" not in lowered:
                continue

            result.append(
                {
                    "symbol": symbol,
                    "text": sentence,
                }
            )

        return result

    @staticmethod
    def _extract_macro(sentences):
        return [
            s for s in sentences
            if "enflasyon" in s.casefold()
            or "faiz" in s.casefold()
        ]