from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path

from ..models.financial_intelligence_models import (
    CanonicalFinancialFact,
    FinancialReportIdentity,
    KapFinancialImportResult,
)


class KapFinancialXlsError(ValueError):
    """KAP HTML-XLS finansal raporu güvenle ayrıştırılamadığında oluşur."""


def _clean_text(parts: list[str] | tuple[str, ...]) -> str:
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _norm_label(value: str) -> str:
    value = value.replace("İ", "I").replace("ı", "i")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


_METRIC_LABELS: dict[str, tuple[str, ...]] = {
    "CASH_EQUIVALENTS": ("Nakit ve Nakit Benzerleri",),
    "CURRENT_ASSETS": ("DÖNEN VARLIKLAR", "TOPLAM DÖNEN VARLIKLAR"),
    "TOTAL_ASSETS": ("TOPLAM VARLIKLAR",),
    "SHORT_TERM_BORROWINGS": ("Kısa Vadeli Borçlanmalar",),
    "CURRENT_PORTION_LT_DEBT": (
        "Uzun Vadeli Borçlanmaların Kısa Vadeli Kısımları",
    ),
    "TRADE_RECEIVABLES": ("Ticari Alacaklar",),
    "INVENTORIES": ("Stoklar",),
    "TRADE_PAYABLES": ("Ticari Borçlar",),
    "CURRENT_LIABILITIES": ("KISA VADELİ YÜKÜMLÜLÜKLER", "TOPLAM KISA VADELİ YÜKÜMLÜLÜKLER"),
    "LONG_TERM_BORROWINGS": ("Uzun Vadeli Borçlanmalar",),
    "NONCURRENT_LIABILITIES": ("UZUN VADELİ YÜKÜMLÜLÜKLER", "TOPLAM UZUN VADELİ YÜKÜMLÜLÜKLER"),
    "PARENT_EQUITY": ("Ana Ortaklığa Ait Özkaynaklar",),
    "TOTAL_LIABILITIES": ("TOPLAM YÜKÜMLÜLÜKLER",),
    "TOTAL_EQUITY": ("TOPLAM ÖZKAYNAKLAR",),
    "REVENUE": ("Hasılat",),
    "COGS": ("Satışların Maliyeti",),
    "GROSS_PROFIT": ("BRÜT KAR (ZARAR)",),
    "OPERATING_PROFIT": (
        "ESAS FAALİYET KARI (ZARARI)",
        "FAALİYET KARI (ZARARI)",
    ),
    "FINANCE_INCOME": ("Finansman Gelirleri",),
    "FINANCE_EXPENSE": ("Finansman Giderleri",),
    "OTHER_OPERATING_INCOME": ("Esas Faaliyetlerden Diğer Gelirler",),
    "OTHER_OPERATING_EXPENSE": ("Esas Faaliyetlerden Diğer Giderler",),
    "INVESTMENT_INCOME": ("Yatırım Faaliyetlerinden Gelirler",),
    "INVESTMENT_EXPENSE": ("Yatırım Faaliyetlerinden Giderler",),
    "EQUITY_METHOD_SHARE": ("Özkaynak Yöntemiyle Değerlenen Yatırımların Karlarından (Zararlarından) Paylar",),
    "MONETARY_GAIN_LOSS": ("Net Parasal Pozisyon Kazançları (Kayıpları)",),
    "TAX_EXPENSE": ("Sürdürülen Faaliyetler Vergi (Gideri) Geliri",),
    "PRETAX_PROFIT": (
        "SÜRDÜRÜLEN FAALİYETLER VERGİ ÖNCESİ KARI (ZARARI)",
        "VERGİ ÖNCESİ KARI (ZARARI)",
    ),
    "NET_INCOME": ("DÖNEM KARI (ZARARI)",),
    "PARENT_NET_INCOME": ("Ana Ortaklık Payları",),
    "OPERATING_CASH_FLOW": ("İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI",),
    "DEPRECIATION_AMORTIZATION": ("Amortisman ve İtfa Gideri İle İlgili Düzeltmeler",),
    "CASH_FROM_OPERATIONS": ("Faaliyetlerden Elde Edilen Nakit Akışları",),
    "TAX_PAID": ("Vergi İadeleri (Ödemeleri)",),
    "CAPEX": ("Maddi ve Maddi Olmayan Duran Varlıkların Alımından Kaynaklanan Nakit Çıkışları",),
    "DIVIDENDS_RECEIVED": ("Alınan Temettüler",),
    "DIVIDENDS_PAID": ("Ödenen Temettüler",),
    "INTEREST_PAID": ("Ödenen Faiz",),
    "INTEREST_RECEIVED": ("Alınan Faiz",),
    "INVESTING_CASH_FLOW": ("YATIRIM FAALİYETLERİNDEN KAYNAKLANAN NAKİT AKIŞLARI",),
    "FINANCING_CASH_FLOW": ("FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI",),
}

_LABEL_TO_METRIC = {
    _norm_label(label): metric
    for metric, labels in _METRIC_LABELS.items()
    for label in labels
}


class _FinancialHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.table_depth = 0
        self.active_table: dict | None = None
        self.tables: list[dict] = []
        self.row: list[dict] | None = None
        self.cell: dict | None = None
        self.cell_table_depth: int | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        attr = dict(attrs)
        if tag == "table":
            self.table_depth += 1
            classes = attr.get("class", "").split()
            if "financial-table" in classes:
                self.active_table = {"depth": self.table_depth, "rows": []}
                self.tables.append(self.active_table)
            return

        if self.active_table is None:
            return

        depth = self.active_table["depth"]
        if tag == "tr" and self.table_depth == depth:
            self.row = []
        elif tag == "td" and self.row is not None and self.table_depth == depth:
            self.cell = {
                "class": attr.get("class", ""),
                "text": [],
                "titles": [],
            }
            self.cell_table_depth = self.table_depth
            self.row.append(self.cell)
        elif self.cell is not None and attr.get("title") not in (None, ""):
            self.cell["titles"].append(attr["title"])

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.active_table is not None:
            depth = self.active_table["depth"]
            if tag == "td" and self.cell is not None and self.table_depth == self.cell_table_depth:
                self.cell = None
                self.cell_table_depth = None
            elif tag == "tr" and self.row is not None and self.table_depth == depth:
                self.active_table["rows"].append(self.row)
                self.row = None

        if tag == "table":
            if self.active_table is not None and self.table_depth == self.active_table["depth"]:
                self.active_table = None
            self.table_depth -= 1


def _parse_decimal(cell: dict) -> Decimal | None:
    raw = cell.get("titles") or []
    candidate = raw[0] if raw else _clean_text(cell.get("text", []))
    candidate = candidate.strip()
    if not candidate:
        return None
    candidate = candidate.replace(".", "").replace(",", ".")
    try:
        return Decimal(candidate)
    except InvalidOperation:
        return None


def _statement_name(table_index: int, first_label: str) -> str:
    n = _norm_label(first_label)
    if "finansal durum tablosu" in n:
        return "BALANCE_SHEET"
    if "kar veya zarar tablosu" in n:
        return "INCOME_STATEMENT"
    if "nakit akis tablosu" in n:
        return "CASH_FLOW"
    if "diger kapsamli gelir" in n:
        return "OCI"
    if "ozkaynaklar degisim" in n:
        return "EQUITY_CHANGES"
    return f"TABLE_{table_index}"


def _extract_meta(text: str, source_name: str) -> FinancialReportIdentity:
    company_match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.I | re.S)
    company_name = re.sub(r"<[^>]+>", "", company_match.group(1)).strip() if company_match else ""

    def field(name: str) -> str | None:
        match = re.search(rf"{re.escape(name)}\s*:\s*([^<\r\n]+)", text, re.I)
        return match.group(1).strip() if match else None

    sent = field("Gönderim Tarihi")
    year = field("Yıl")
    period = field("Periyot")
    currency_match = re.search(r"Sunum Para Birimi\s*</td>\s*<td[^>]*>\s*([^<]+)", text, re.I | re.S)
    scope_match = re.search(r"Finansal Tablo Niteliği\s*</td>\s*<td[^>]*>\s*([^<]+)", text, re.I | re.S)
    date_match = re.search(r"Cari Dönem\s*<br>\s*(\d{2}\.\d{2}\.\d{4})", text, re.I | re.S)

    filename = Path(source_name).name
    fn = re.match(r"(?P<symbol>[A-Z0-9]+)_(?P<disc>\d+)_(?P<year>\d{4})_(?P<period>\d+)\.xls$", filename, re.I)
    symbol = fn.group("symbol").upper() if fn else "UNKNOWN"
    disclosure_id = fn.group("disc") if fn else None
    fiscal_year = int(year or (fn.group("year") if fn else 0))
    fiscal_period = int(period or (fn.group("period") if fn else 0))
    if not fiscal_year or not fiscal_period:
        raise KapFinancialXlsError("KAP rapor yıl/periyot kimliği bulunamadı.")

    if date_match:
        report_date = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
    else:
        month = {1: 3, 2: 6, 3: 9, 4: 12}.get(fiscal_period)
        if month is None:
            raise KapFinancialXlsError("KAP rapor tarihi çıkarılamadı.")
        report_date = date(fiscal_year, month, 30 if month in (6, 9) else 31)

    published_at = None
    if sent:
        try:
            published_at = datetime.strptime(sent, "%d.%m.%Y %H:%M:%S")
        except ValueError as exc:
            raise KapFinancialXlsError("KAP gönderim tarihi çözümlenemedi.") from exc

    currency_text = currency_match.group(1).strip() if currency_match else "1 TL"
    scale = Decimal("1000") if "1.000" in currency_text or "1000" in currency_text else Decimal("1")
    currency = "TRY" if "TL" in currency_text.upper() else currency_text.upper()
    scope = scope_match.group(1).strip().upper() if scope_match else "UNKNOWN"

    return FinancialReportIdentity(
        symbol=symbol,
        company_name=company_name,
        disclosure_id=disclosure_id,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        report_date=report_date,
        published_at=published_at,
        consolidation_scope=scope,
        currency=currency,
        currency_scale=scale,
    )


def import_kap_financial_xls_bytes(payload: bytes, *, source_name: str = "report.xls") -> KapFinancialImportResult:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise KapFinancialXlsError("KAP XLS UTF-8 HTML olarak okunamadı.") from exc

    identity = _extract_meta(text, source_name)
    parser = _FinancialHtmlParser()
    parser.feed(text)
    if not parser.tables:
        raise KapFinancialXlsError("KAP finansal tablo blokları bulunamadı.")

    facts: list[CanonicalFinancialFact] = []
    unmapped: set[str] = set()

    for table_index, table in enumerate(parser.tables):
        rows = table["rows"]
        if not rows:
            continue
        header_cells = [c for c in rows[0] if "context-header" in c.get("class", "")]
        period_labels = [_clean_text(c.get("text", [])) for c in header_cells]
        first_label = ""
        for row in rows[1:]:
            if len(row) > 1:
                candidate = _clean_text(row[1].get("text", []))
                if candidate:
                    first_label = candidate
                    break
        statement = _statement_name(table_index, first_label)

        for row in rows[1:]:
            if len(row) < 2:
                continue
            label = _clean_text(row[1].get("text", []))
            if not label:
                continue
            value_cells = [c for c in row if "taxonomy-context-value" in c.get("class", "")]
            if not value_cells:
                continue
            metric = _LABEL_TO_METRIC.get(_norm_label(label))
            if metric is None and any(_parse_decimal(c) is not None for c in value_cells):
                unmapped.add(label)
            note_ref = None
            if len(row) > 2 and "taxonomy-footnote-cell" in row[2].get("class", ""):
                note_ref = _clean_text(row[2].get("text", [])) or None
            for index, cell in enumerate(value_cells):
                value = _parse_decimal(cell)
                if value is None:
                    continue
                period_label = period_labels[index] if index < len(period_labels) else f"COLUMN_{index + 1}"
                facts.append(CanonicalFinancialFact(
                    statement=statement,
                    metric_code=metric,
                    source_label=label,
                    period_label=period_label,
                    value=value,
                    note_ref=note_ref,
                ))

    if not facts:
        raise KapFinancialXlsError("KAP raporundan sayısal finansal gerçek çıkarılamadı.")

    return KapFinancialImportResult(
        identity=identity,
        facts=tuple(facts),
        unmapped_labels=tuple(sorted(unmapped)),
        source_sha256=hashlib.sha256(payload).hexdigest(),
    )


def import_kap_financial_xls(path: str | Path) -> KapFinancialImportResult:
    file_path = Path(path)
    if not file_path.is_file():
        raise KapFinancialXlsError(f"KAP XLS bulunamadı: {file_path}")
    return import_kap_financial_xls_bytes(file_path.read_bytes(), source_name=file_path.name)
