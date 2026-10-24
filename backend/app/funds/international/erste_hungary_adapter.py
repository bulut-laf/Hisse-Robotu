from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from .contract import (
    InternationalFundSnapshot,
    canonical_isin_fund_id,
    normalize_currency,
    normalize_isin,
)


MARKET = "HU"
DISTRIBUTION = "ERSTE_HUNGARY"
INSTRUMENT_TYPE = "FUND"


def _pick(row: Mapping[str, Any], *names: str) -> Any:
    values = {str(key).casefold(): value for key, value in row.items()}
    for name in names:
        value = values.get(name.casefold())
        if value not in (None, ""):
            return value
    return None


def _text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _decimal(value: object, *, percent: bool = False) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        result = value
    else:
        text = str(value).strip()
        if not text:
            return None

        text = (
            text.replace("\u00a0", "")
            .replace(" ", "")
            .replace("%", "")
        )

        # Localized HU/EU style: 1.234,56 -> 1234.56
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(",", ".")

        text = re.sub(r"[^0-9+\-.]", "", text)
        if text in {"", "+", "-", ".", "+.", "-."}:
            return None

        try:
            result = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"INVALID_DECIMAL:{value}") from exc

    return result / Decimal("100") if percent else result


def _date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    for fmt in (
        "%Y-%m-%d",
        "%Y.%m.%d",
        "%Y.%m.%d.",
        "%d.%m.%Y",
        "%d.%m.%Y.",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    raise ValueError(f"INVALID_DATE:{text}")


def normalize_erste_hungary_row(
    row: Mapping[str, Any],
    *,
    fetched_at: datetime | None = None,
) -> InternationalFundSnapshot:
    isin = normalize_isin(
        _pick(row, "isin", "ISIN", "instrument_isin", "security_isin")
    )
    name = _text(_pick(row, "name", "fund_name", "alap_neve", "megnevezes"))
    if not name:
        raise ValueError(f"FUND_NAME_MISSING:{isin}")

    source_url = _text(_pick(row, "source_url", "url"))
    if not source_url:
        raise ValueError(f"SOURCE_URL_MISSING:{isin}")

    return InternationalFundSnapshot(
        canonical_fund_id=canonical_isin_fund_id(isin),
        isin=isin,
        market=MARKET,
        distribution=DISTRIBUTION,
        instrument_type=INSTRUMENT_TYPE,

        name=name,
        fund_manager=_text(
            _pick(row, "fund_manager", "manager", "alapkezelo")
        ),
        category_raw=_text(
            _pick(row, "category_raw", "category", "kategoria")
        ),
        category_normalized=_text(
            _pick(row, "category_normalized")
        ),
        currency=normalize_currency(
            _pick(row, "currency", "devizanem", "denomination_currency")
        ),
        risk_raw=_text(
            _pick(row, "risk_raw", "risk", "kockazat")
        ),
        region=_text(
            _pick(row, "region", "regio")
        ),

        nav=_decimal(
            _pick(row, "nav", "arfolyam", "unit_price")
        ),
        nav_date=_date(
            _pick(row, "nav_date", "arfolyam_datum", "price_date")
        ),
        net_asset_value=_decimal(
            _pick(row, "net_asset_value", "netto_eszkozertek")
        ),
        inception_date=_date(
            _pick(row, "inception_date", "indulas", "launch_date")
        ),
        settlement=_text(
            _pick(row, "settlement", "elszamolas", "valor")
        ),

        return_1m=_decimal(
            _pick(row, "return_1m", "hozam_1m", "1m_return"),
            percent=True,
        ),
        return_3m=_decimal(
            _pick(row, "return_3m", "hozam_3m", "3m_return"),
            percent=True,
        ),
        return_6m=_decimal(
            _pick(row, "return_6m", "hozam_6m", "6m_return"),
            percent=True,
        ),
        return_ytd=_decimal(
            _pick(row, "return_ytd", "hozam_ytd", "ytd_return"),
            percent=True,
        ),
        return_1y=_decimal(
            _pick(row, "return_1y", "hozam_1y", "1y_return"),
            percent=True,
        ),
        return_5y=_decimal(
            _pick(row, "return_5y", "hozam_5y", "5y_return"),
            percent=True,
        ),

        volatility_1y=_decimal(
            _pick(row, "volatility_1y", "volatilitas_1y"),
            percent=True,
        ),
        volatility_3y=_decimal(
            _pick(row, "volatility_3y", "volatilitas_3y"),
            percent=True,
        ),
        max_drawdown_1y=_decimal(
            _pick(row, "max_drawdown_1y", "max_visszaeses_1y"),
            percent=True,
        ),
        max_drawdown_5y=_decimal(
            _pick(row, "max_drawdown_5y", "max_visszaeses_5y"),
            percent=True,
        ),

        total_expense_ratio=_decimal(
            _pick(row, "total_expense_ratio", "ter", "koltseghanyad"),
            percent=True,
        ),
        allocation_known=bool(
            _pick(row, "allocation_known", "allocation")
        ),

        erste_access_status=_text(
            _pick(row, "erste_access_status", "access_status")
        ),
        source_url=source_url,
        source_date=_date(
            _pick(row, "source_date", "data_date")
        ),
        fetched_at=fetched_at or datetime.now(timezone.utc),
    )
