from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
import html as html_lib
import re
from urllib.parse import quote

from .contract import InternationalFundSnapshot, canonical_isin_fund_id
from .erste_hungary_adapter import _date, _decimal
from .erste_hungary_source import ERSTE_MARKET_BASE_URL, fetch_text


COMPARISON_URL = f"{ERSTE_MARKET_BASE_URL}/befektetesi_alapok/osszehasonlitas?funds={{isin}}"

LABEL_NAME = "Megnevez\u00e9s"
LABEL_MANAGER = "Alapkezel\u0151"
LABEL_INCEPTION = "Indul\u00e1s"
LABEL_CURRENCY = "Deviza"
LABEL_RETURN_YTD = "Akt. \u00e9vi hozam (%)"
LABEL_RETURN_1Y = "1 \u00e9ves hozam (%)"
LABEL_RETURN_5Y = "5 \u00e9ves hozam (%)"
LABEL_VOL_1Y = "1 \u00e9ves volatilit\u00e1s (%)"
LABEL_VOL_3Y = "3 \u00e9ves volatilit\u00e1s (%)"
LABEL_VOL_5Y = "5 \u00e9ves volatilit\u00e1s (%)"
LABEL_DD_1Y = "1 \u00e9ves max drawdown (%)"
LABEL_DD_5Y = "5 \u00e9ves max drawdown (%)"
LABEL_NAV = "\u00c1rfolyam"
LABEL_NET_ASSET = "Nett\u00f3 eszk\u00f6z\u00e9rt\u00e9k"
LABEL_CATEGORY = "Kateg\u00f3ria"
LABEL_RISK = "Kock\u00e1zat"

VALID_RISK_VALUES = {
    "Magas",
    "K\u00f6zepes",
    "Alacsony",
}


class _LineCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def html_text_tokens(html: str) -> tuple[str, ...]:
    parser = _LineCollector()
    parser.feed(html or "")
    return tuple(parser.parts)


def normalized_text_lines(html: str) -> tuple[str, ...]:
    tokens = html_text_tokens(html)
    lines: list[str] = []
    for token in tokens:
        cleaned = html_lib.unescape(token).strip()
        if cleaned:
            lines.append(cleaned)
    return tuple(lines)


def _find_after(
    lines: tuple[str, ...],
    label: str,
) -> str | None:
    target = label.casefold()
    for index, line in enumerate(lines):
        if line.casefold() == target and index + 1 < len(lines):
            return lines[index + 1]
    return None


def _clean_value(value: str | None) -> str | None:
    if value in (None, "", "-"):
        return None
    return value

def _normalize_risk_value(value: str | None) -> str | None:
    value = _clean_value(value)
    if value in VALID_RISK_VALUES:
        return value
    return None

KNOWN_LABELS = {
    "ISIN",
    LABEL_NAME,
    LABEL_MANAGER,
    LABEL_INCEPTION,
    LABEL_CURRENCY,
    LABEL_RETURN_YTD,
    LABEL_RETURN_1Y,
    LABEL_RETURN_5Y,
    LABEL_VOL_1Y,
    LABEL_VOL_3Y,
    LABEL_VOL_5Y,
    LABEL_DD_1Y,
    LABEL_DD_5Y,
    LABEL_NAV,
    LABEL_NET_ASSET,
    LABEL_CATEGORY,
    LABEL_RISK,
}


def _find_optional_value_after_label(
    lines: tuple[str, ...],
    label: str,
) -> str | None:
    target = label.casefold()

    for index, line in enumerate(lines):
        if line.casefold() != target:
            continue

        if index + 1 >= len(lines):
            return None

        candidate = lines[index + 1]
        if candidate.casefold() in {item.casefold() for item in KNOWN_LABELS}:
            return None

        return candidate

    return None


def _parse_net_asset_value(
    value: str | None,
) -> tuple[Decimal | None, str | None]:
    if not value or value == "-":
        return None, None

    match = re.match(r"^\s*([\d\s.,]+)\s+([A-Z]{3})\s*$", value)
    if not match:
        return _decimal(value), None

    amount = match.group(1).replace(" ", "")
    currency = match.group(2)
    return _decimal(amount), currency


def _fund_block_for_isin(
    lines: tuple[str, ...],
    isin: str,
) -> tuple[str, ...]:
    expected = isin.strip().upper()

    try:
        isin_index = next(
            index
            for index, line in enumerate(lines)
            if line.strip().upper() == expected
        )
    except StopIteration:
        raise ValueError(f"ERSTE_COMPARISON_ISIN_MISSING:{expected}")

    start = max(0, isin_index - 6)
    for index in range(isin_index, max(-1, isin_index - 15), -1):
        if lines[index].casefold() == LABEL_NAME.casefold():
            start = index
            break

    end = min(len(lines), isin_index + 80)

    for index in range(isin_index + 1, min(len(lines), isin_index + 80)):
        if (
            lines[index].casefold() == LABEL_NAME.casefold()
            and index > isin_index + 2
        ):
            end = index
            break

    return tuple(lines[start:end])


def _extract_nav_date_from_block(
    block: tuple[str, ...],
    nav_text: str | None,
) -> date | None:
    if not nav_text:
        return None

    try:
        nav_index = next(
            index
            for index, line in enumerate(block)
            if line.strip() == nav_text.strip()
        )
    except StopIteration:
        return None

    for candidate in block[nav_index + 1:nav_index + 6]:
        if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\.?", candidate.strip()):
            return _date(candidate.strip())

    return None


@dataclass(frozen=True, slots=True)
class ErsteComparisonFund:
    isin: str
    name: str
    fund_manager: str | None
    inception_date: date | None
    currency: str | None
    return_ytd: Decimal | None
    return_1y: Decimal | None
    return_5y: Decimal | None
    volatility_1y: Decimal | None
    volatility_3y: Decimal | None
    volatility_5y: Decimal | None
    max_drawdown_1y: Decimal | None
    max_drawdown_5y: Decimal | None
    nav: Decimal | None
    nav_date: date | None
    net_asset_value: Decimal | None
    category_raw: str | None
    risk_raw: str | None
    source_url: str


def parse_single_fund_comparison_html(
    html: str,
    *,
    source_url: str,
    expected_isin: str,
) -> ErsteComparisonFund:
    lines = normalized_text_lines(html)
    expected = expected_isin.strip().upper()
    block = _fund_block_for_isin(lines, expected)

    isin = _find_after(block, "ISIN")
    if isin is None:
        if expected in {line.strip().upper() for line in block}:
            isin = expected
        else:
            raise ValueError("ERSTE_COMPARISON_ISIN_MISSING")

    isin = isin.strip().upper()
    if isin != expected:
        raise ValueError(
            f"ERSTE_COMPARISON_ISIN_MISMATCH:{isin}:{expected}"
        )

    name = _clean_value(_find_after(block, LABEL_NAME))
    if not name:
        raise ValueError(f"ERSTE_COMPARISON_NAME_MISSING:{isin}")

    nav_text = _clean_value(_find_after(block, LABEL_NAV))
    nav_value = _decimal(nav_text)
    nav_date_value = _extract_nav_date_from_block(block, nav_text)

    net_asset_value, _net_asset_currency = _parse_net_asset_value(
        _clean_value(_find_after(block, LABEL_NET_ASSET))
    )

    return ErsteComparisonFund(
        isin=isin,
        name=name,
        fund_manager=_clean_value(_find_after(block, LABEL_MANAGER)),
        inception_date=_date(
            _clean_value(
                _find_optional_value_after_label(
                    block,
                    LABEL_INCEPTION,
                )
            )
        ),
        currency=_clean_value(_find_after(block, LABEL_CURRENCY)),
        return_ytd=_decimal(
            _clean_value(_find_after(block, LABEL_RETURN_YTD)),
            percent=True,
        ),
        return_1y=_decimal(
            _clean_value(_find_after(block, LABEL_RETURN_1Y)),
            percent=True,
        ),
        return_5y=_decimal(
            _clean_value(_find_after(block, LABEL_RETURN_5Y)),
            percent=True,
        ),
        volatility_1y=_decimal(
            _clean_value(_find_after(block, LABEL_VOL_1Y)),
            percent=True,
        ),
        volatility_3y=_decimal(
            _clean_value(_find_after(block, LABEL_VOL_3Y)),
            percent=True,
        ),
        volatility_5y=_decimal(
            _clean_value(_find_after(block, LABEL_VOL_5Y)),
            percent=True,
        ),
        max_drawdown_1y=_decimal(
            _clean_value(_find_after(block, LABEL_DD_1Y)),
            percent=True,
        ),
        max_drawdown_5y=_decimal(
            _clean_value(_find_after(block, LABEL_DD_5Y)),
            percent=True,
        ),
        nav=nav_value,
        nav_date=nav_date_value,
        net_asset_value=net_asset_value,
        category_raw=_clean_value(_find_after(block, LABEL_CATEGORY)),
        risk_raw=_normalize_risk_value(
            _find_after(
                block,
                LABEL_RISK,
            )
        ),
        source_url=source_url,
    )


def comparison_url_for_isin(isin: str) -> str:
    normalized = isin.strip().upper()
    return COMPARISON_URL.format(isin=quote(normalized, safe=""))


def fetch_single_fund_comparison(
    isin: str,
    *,
    timeout_seconds: float = 30.0,
) -> ErsteComparisonFund:
    url = comparison_url_for_isin(isin)
    html = fetch_text(
        url,
        timeout_seconds=timeout_seconds,
        user_agent="Hisse-Robotu/Erste-Hungary-Comparison-v1",
    )
    return parse_single_fund_comparison_html(
        html,
        source_url=url,
        expected_isin=isin,
    )


def comparison_to_snapshot(
    fund: ErsteComparisonFund,
    *,
    fetched_at: datetime | None = None,
) -> InternationalFundSnapshot:
    return InternationalFundSnapshot(
        canonical_fund_id=canonical_isin_fund_id(fund.isin),
        isin=fund.isin,
        market="HU",
        distribution="ERSTE_HUNGARY",
        instrument_type="FUND",
        name=fund.name,
        fund_manager=fund.fund_manager,
        category_raw=fund.category_raw,
        category_normalized=None,
        currency=fund.currency,
        risk_raw=fund.risk_raw,
        region=None,
        nav=fund.nav,
        nav_date=fund.nav_date,
        net_asset_value=fund.net_asset_value,
        inception_date=fund.inception_date,
        settlement=None,
        return_1m=None,
        return_3m=None,
        return_6m=None,
        return_ytd=fund.return_ytd,
        return_1y=fund.return_1y,
        return_5y=fund.return_5y,
        volatility_1y=fund.volatility_1y,
        volatility_3y=fund.volatility_3y,
        max_drawdown_1y=fund.max_drawdown_1y,
        max_drawdown_5y=fund.max_drawdown_5y,
        total_expense_ratio=None,
        allocation_known=False,
        erste_access_status="DISCOVERED_IN_ERSTE_UNIVERSE",
        source_url=fund.source_url,
        source_date=fund.nav_date,
        fetched_at=fetched_at or datetime.now(timezone.utc),
    )