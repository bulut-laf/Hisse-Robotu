from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from datetime import datetime
from decimal import Decimal
import re
from typing import Iterable
from urllib.request import Request, urlopen

from .kap_portfolio_auto_ingestion import _fetch_targeted_fund_disclosures


_COST_SUBJECT = "fon toplam gider oranı ve fon toplam giderinin dağılımı"
_PERCENT_RE = re.compile(r"%\s*([0-9]+(?:[.,][0-9]+)?)")


@dataclass(frozen=True, slots=True)
class KapFundCostDisclosure:
    fund_code: str
    notification_id: str
    publish_date: str
    subject: str
    summary: str


@dataclass(frozen=True, slots=True)
class KapFundCostMetrics:
    fund_code: str
    notification_id: str
    annual_maximum_expense_ratio_values: tuple[Decimal, ...]
    period_maximum_expense_ratio_values: tuple[Decimal, ...]
    realized_expense_ratio_values: tuple[Decimal, ...]
    realized_net_expense_ratio_values: tuple[Decimal, ...]
    annual_management_fee_values: tuple[Decimal, ...]
    current_period_realized_expense_ratio: Decimal
    current_period_net_realized_expense_ratio: Decimal | None



class _KapCostRowParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_row = False
        self._row_depth = 0
        self._cell_tag = None
        self._cell_text = []
        self._cell_attrs = {}
        self._cells = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        low = tag.lower()
        attrs_map = dict(attrs)
        if low == "tr":
            if not self._in_row:
                self._in_row = True
                self._row_depth = 1
                self._cells = []
            else:
                self._row_depth += 1
            return
        if self._in_row and low in ("td", "th"):
            self._cell_tag = low
            self._cell_text = []
            self._cell_attrs = attrs_map

    def handle_data(self, data):
        if self._in_row and self._cell_tag is not None:
            self._cell_text.append(data)

    def handle_endtag(self, tag):
        low = tag.lower()
        if self._in_row and self._cell_tag is not None and low == self._cell_tag:
            text = re.sub(r"\s+", " ", "".join(self._cell_text)).strip()
            self._cells.append((text, self._cell_attrs))
            self._cell_tag = None
            self._cell_text = []
            self._cell_attrs = {}
            return
        if low == "tr" and self._in_row:
            self._row_depth -= 1
            if self._row_depth == 0:
                self.rows.append(tuple(self._cells))
                self._in_row = False


def _visible_tr_percent_for_marker(raw_html: str, marker: str) -> Decimal | None:
    parser = _KapCostRowParser()
    parser.feed(raw_html)
    for row in parser.rows:
        if not row or marker not in row[0][0]:
            continue
        for text, attrs in row:
            classes = set(str(attrs.get("class") or "").split())
            if (
                "taxonomy-context-value" in classes
                and "content-tr" in classes
                and "col-order-class-3" in classes
            ):
                values = _ratio_values(text)
                return values[0] if len(values) == 1 else None
    return None



def _ratio_values(block: str) -> tuple[Decimal, ...]:
    values: list[Decimal] = []
    for raw in _PERCENT_RE.findall(block):
        value = Decimal(raw.replace(",", ".")) / Decimal("100")
        values.append(value)
    return tuple(values)


def _marker_block(text: str, marker: str) -> str:
    start = text.find(marker)
    if start < 0:
        return ""
    next_marker = text.find("oda_", start + len(marker))
    if next_marker < 0:
        return text[start:]
    return text[start:next_marker]


def discover_kap_fund_cost_disclosures(
    fund_codes: Iterable[str],
    *,
    timeout_seconds: int = 30,
) -> tuple[KapFundCostDisclosure, ...]:
    raw = _fetch_targeted_fund_disclosures(tuple(fund_codes), timeout_seconds)
    if not isinstance(raw, list):
        return ()

    result: list[KapFundCostDisclosure] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        subject = str(row.get("subject") or "").strip()
        if _COST_SUBJECT not in subject.lower():
            continue
        fund_code = str(row.get("fundCode") or "").strip().upper()
        notification_id = str(row.get("disclosureIndex") or "").strip()
        if not fund_code or not notification_id:
            continue
        result.append(
            KapFundCostDisclosure(
                fund_code=fund_code,
                notification_id=notification_id,
                publish_date=str(row.get("publishDate") or "").strip(),
                subject=subject,
                summary=str(row.get("summary") or "").strip(),
            )
        )

    def _key(item: KapFundCostDisclosure) -> tuple[int, str]:
        try:
            return (int(item.notification_id), item.publish_date)
        except ValueError:
            return (-1, item.publish_date)

    return tuple(sorted(result, key=_key, reverse=True))


def fetch_kap_fund_cost_page(
    notification_id: str,
    *,
    timeout_seconds: int = 30,
) -> str:
    notification_id = str(notification_id).strip()
    if not notification_id.isdigit():
        raise ValueError("notification_id numeric olmalıdır.")

    request = Request(
        f"https://www.kap.org.tr/tr/Bildirim/{notification_id}",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,*/*",
            "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu",
        },
        method="GET",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_kap_fund_cost_metrics(
    raw_html: str,
    *,
    fund_code: str,
    notification_id: str,
) -> KapFundCostMetrics:
    # KAP detail HTML exposes XBRL concept ids in the rendered body.  Preserve
    # every percentage value in each concept block instead of guessing which
    # column should feed F5.  Semantic selection belongs to the binding layer.
    text = re.sub(r"\s+", " ", raw_html)

    markers = {
        "annual_maximum_expense_ratio_values":
            "oda_AnnualMaximumFundTotalExpenseRatio|",
        "period_maximum_expense_ratio_values":
            "oda_MaximumFundTotalExpsenseRatioThatFallToRelatedPeriod|",
        "realized_expense_ratio_values":
            "oda_FundTotalExpenseRatioRealizedAtTheEndOfPeriod|",
        "realized_net_expense_ratio_values":
            "oda_NetFundTotalExpenseRatioRealizedAtTheEndOfPeriod|",
        "annual_management_fee_values":
            "oda_AnnualManagementFee|",
    }

    parsed = {
        name: _ratio_values(_marker_block(text, marker))
        for name, marker in markers.items()
    }

    current_realized = _visible_tr_percent_for_marker(
        raw_html,
        "oda_FundTotalExpenseRatioRealizedAtTheEndOfPeriod|",
    )
    current_net_realized = _visible_tr_percent_for_marker(
        raw_html,
        "oda_NetFundTotalExpenseRatioRealizedAtTheEndOfPeriod|",
    )

    if current_realized is None:
        raise ValueError("KAP_COST_CURRENT_REALIZED_EXPENSE_RATIO_MISSING")

    if not parsed["annual_maximum_expense_ratio_values"]:
        raise ValueError("KAP_COST_ANNUAL_MAXIMUM_EXPENSE_RATIO_MISSING")
    if not parsed["realized_expense_ratio_values"]:
        raise ValueError("KAP_COST_REALIZED_EXPENSE_RATIO_MISSING")

    return KapFundCostMetrics(
        fund_code=str(fund_code).strip().upper(),
        notification_id=str(notification_id).strip(),
        current_period_realized_expense_ratio=current_realized,
        current_period_net_realized_expense_ratio=current_net_realized,
        **parsed,
    )


def fetch_latest_kap_fund_cost_metrics(
    fund_code: str,
    *,
    timeout_seconds: int = 30,
) -> KapFundCostMetrics:
    disclosures = discover_kap_fund_cost_disclosures(
        (fund_code,),
        timeout_seconds=timeout_seconds,
    )
    if not disclosures:
        raise ValueError("KAP_COST_DISCLOSURE_NOT_FOUND")

    latest = disclosures[0]
    html = fetch_kap_fund_cost_page(
        latest.notification_id,
        timeout_seconds=timeout_seconds,
    )
    return parse_kap_fund_cost_metrics(
        html,
        fund_code=latest.fund_code,
        notification_id=latest.notification_id,
    )
