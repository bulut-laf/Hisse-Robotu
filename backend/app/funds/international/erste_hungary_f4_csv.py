from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable

BAMOSZ_DOWNLOAD_URL = "https://www.bamosz.hu/bamosz-public-alapoldal-portlet/kuka.download"
TARGET_ISINS = (
    "AT0000627476", "AT0000A00G88", "AT0000A00GA2",
    "AT0000A00G96", "AT0000A00GC8", "AT0000A00GE4",
    "AT0000A00GF1",
)

@dataclass(frozen=True)
class DailyNavRow:
    date: date
    price: Decimal | None
    nav: Decimal
    turnover: Decimal | None

@dataclass(frozen=True)
class CsvEvidence:
    isin: str
    encoding: str
    delimiter: str
    header: tuple[str, ...]
    rows: tuple[DailyNavRow, ...]
    download_bytes: int
    fund_name: str | None

def _norm(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "").replace("\ufeff", "").strip()).casefold()

def _decimal(value: object) -> Decimal | None:
    s = str(value or "").strip().replace("\u00a0", "").replace(" ", "")
    if not s or s in {"-", "—", "–"}:
        return None
    # Hungarian exports commonly use decimal comma and dot thousands separators.
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None

def _date(value: object) -> date | None:
    s = str(value or "").strip()
    for fmt in ("%Y.%m.%d.", "%Y.%m.%d", "%Y-%m-%d", "%d.%m.%Y.", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

def _decode(raw: bytes) -> tuple[str, str]:
    for encoding in ("iso-8859-2", "cp1250", "utf-8-sig"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("iso-8859-2", errors="replace"), "iso-8859-2-replace"

def parse_bamosz_csv(raw: bytes, isin: str) -> CsvEvidence:
    if not raw:
        raise ValueError("EMPTY_CSV_BODY")
    text, encoding = _decode(raw)
    lines = text.splitlines()
    # Locate the real daily table header; do not assume metadata rows are the header.
    header_line = None
    delimiter = ";"
    header = None
    for i, line in enumerate(lines):
        for candidate in (";", "\t", ","):
            try:
                cells = next(csv.reader([line], delimiter=candidate, quotechar='"', skipinitialspace=True))
            except csv.Error:
                continue
            n = [_norm(c) for c in cells]
            has_date = any(x == "dátum" or x == "datum" for x in n)
            has_price = any(x in {"árfolyam", "arfolyam"} for x in n)
            has_nav = any(x in {"neé", "nettó eszközérték", "netto eszkoz ertek"} for x in n)
            if has_date and has_price and has_nav:
                header_line, delimiter, header = i, candidate, [c.strip().strip('"') for c in cells]
                break
        if header_line is not None:
            break
    if header_line is None or header is None:
        preview = " | ".join(lines[:5])[:500]
        raise ValueError(f"CSV_DAILY_HEADER_NOT_FOUND:{isin}:preview={preview!r}")

    norm_header = [_norm(x) for x in header]
    def find_index(*aliases: str) -> int | None:
        wanted = {_norm(x) for x in aliases}
        return next((i for i, x in enumerate(norm_header) if x in wanted), None)

    date_i = find_index("Dátum", "Datum")
    price_i = find_index("Árfolyam", "Arfolyam")
    nav_i = find_index("NEÉ", "Nettó eszközérték", "Netto eszkoz ertek")
    turnover_i = find_index("Napi befjegy. forgalom", "Napi bef. jegy forgalom",
                            "Napi befjegy forgalom", "Napi bef. jegy forgalom")
    if date_i is None or nav_i is None:
        raise ValueError(f"CSV_REQUIRED_COLUMNS_MISSING:{isin}")

    rows: list[DailyNavRow] = []
    for line in lines[header_line + 1:]:
        if not line.strip():
            continue
        try:
            cells = next(csv.reader([line], delimiter=delimiter, quotechar='"', skipinitialspace=True))
        except csv.Error:
            continue
        if len(cells) <= max(date_i, nav_i):
            continue
        d = _date(cells[date_i])
        nav = _decimal(cells[nav_i])
        if d is None or nav is None or nav <= 0:
            continue
        price = _decimal(cells[price_i]) if price_i is not None and len(cells) > price_i else None
        turnover = _decimal(cells[turnover_i]) if turnover_i is not None and len(cells) > turnover_i else None
        rows.append(DailyNavRow(d, price, nav, turnover))

    # Deduplicate by date deterministically and sort ascending.
    by_date = {r.date: r for r in rows}
    valid = tuple(by_date[d] for d in sorted(by_date))
    fund_name = None
    for line in lines[:header_line]:
        try:
            cells = next(csv.reader([line], delimiter=delimiter, quotechar='"'))
        except csv.Error:
            continue
        if len(cells) >= 2 and _norm(cells[0]) in {"alap neve:", "fund name:"}:
            fund_name = cells[1].strip()
            break
    return CsvEvidence(isin.upper(), encoding, delimiter, tuple(header), valid, len(raw), fund_name)

def fund_size_change(rows: Iterable[DailyNavRow]) -> Decimal | None:
    ordered = sorted(rows, key=lambda r: r.date)
    if len(ordered) < 2:
        return None
    previous, latest = ordered[-2], ordered[-1]
    if previous.nav <= 0 or latest.nav <= 0:
        return None
    return latest.nav / previous.nav - Decimal("1")

def net_flow_ratio(*, official_net_investor_flow: Decimal | None,
                   prior_fund_nav: Decimal | None) -> Decimal | None:
    """Return only an explicitly sourced net investor flow / prior NAV ratio."""
    if official_net_investor_flow is None or prior_fund_nav is None or prior_fund_nav <= 0:
        return None
    return official_net_investor_flow / prior_fund_nav
