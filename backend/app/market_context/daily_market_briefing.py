from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


_SYMBOL_RE = re.compile(r"\b([A-ZÇĞİÖŞÜ]{3,7})(?:\.IS)?\b")
_VIEW_RE = re.compile(
    r"(?<![A-ZÇĞİÖŞÜ])(AL|TUT|SAT|NÖTR|NOTR|OUTPERFORM|UNDERPERFORM)"
    r"(?![A-ZÇĞİÖŞÜ])",
    re.IGNORECASE,
)
_TARGET_RE = re.compile(
    r"(?:hedef\s*(?:fiyat|değer|deger)?|hf)\s*[:=\-]?\s*"
    r"([0-9][0-9\s\.]*[\.,]?[0-9]*)",
    re.IGNORECASE,
)
_POTENTIAL_RE = re.compile(
    r"(?:potansiyel|getiri\s*potansiyeli)\s*[:=\-]?\s*%?\s*"
    r"([+\-]?[0-9]+(?:[\.,][0-9]+)?)\s*%?",
    re.IGNORECASE,
)

_EXCLUDED_SYMBOLS = {
    "ABD",
    "BIST",
    "BIST30",
    "BIST100",
    "KAP",
    "TCMB",
    "TÜFE",
    "TUFE",
    "SPK",
    "TL",
    "USD",
    "EUR",
}

_VIEW_LABELS = {
    "AL": "AL",
    "TUT": "TUT",
    "SAT": "SAT",
    "NÖTR": "NÖTR",
    "NOTR": "NÖTR",
    "OUTPERFORM": "OUTPERFORM",
    "UNDERPERFORM": "UNDERPERFORM",
}


@dataclass(frozen=True, slots=True)
class ProcessedMarketReport:
    report_id: str
    source: str
    report_type: str
    report_date: str
    raw_text: str
    file_path: Path

    @property
    def character_count(self) -> int:
        return len(self.raw_text)


@dataclass(frozen=True, slots=True)
class SourceRecommendation:
    source: str
    symbol: str
    source_view: str
    target_price: float | None
    potential_percent: float | None
    evidence: str
    report_id: str


@dataclass(frozen=True, slots=True)
class DailyMarketBriefingSnapshot:
    review_date: str
    reports: tuple[ProcessedMarketReport, ...]
    recommendations: tuple[SourceRecommendation, ...]

    @property
    def source_names(self) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for report in self.reports:
            key = report.source.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(report.source)
        return tuple(ordered)

    @property
    def report_count(self) -> int:
        return len(self.reports)

    @property
    def recommendation_count(self) -> int:
        return len(self.recommendations)


def normalize_review_date(value: object | None) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = str(value or "").strip()
    if not text:
        return date.today().isoformat()

    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return text[:10]


def processed_reports_directory(project_root: str | Path, review_date: object) -> Path:
    root = Path(project_root)
    return root / "backend" / "data" / "market_context_processed" / normalize_review_date(review_date)


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _read_report_file(path: Path, review_date: str) -> ProcessedMarketReport | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    raw_text = _safe_text(payload.get("raw_text"))
    if not raw_text:
        return None

    source = _safe_text(
        payload.get("source")
        or payload.get("source_name")
        or payload.get("kaynak"),
        "Kaynak belirtilmedi",
    )
    report_type = _safe_text(
        payload.get("report_type")
        or payload.get("input_type")
        or payload.get("type"),
        "—",
    )
    report_id = _safe_text(
        payload.get("report_id")
        or payload.get("context_id")
        or payload.get("id"),
        path.stem,
    )
    report_date = _safe_text(
        payload.get("report_date")
        or payload.get("date")
        or payload.get("archive_date"),
        review_date,
    )

    return ProcessedMarketReport(
        report_id=report_id,
        source=source,
        report_type=report_type,
        report_date=report_date[:10],
        raw_text=raw_text,
        file_path=path,
    )


def load_processed_reports(
    project_root: str | Path,
    review_date: object,
) -> tuple[ProcessedMarketReport, ...]:
    day = normalize_review_date(review_date)
    directory = processed_reports_directory(project_root, day)
    if not directory.is_dir():
        return ()

    reports: list[ProcessedMarketReport] = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.name.casefold()):
        report = _read_report_file(path, day)
        if report is not None:
            reports.append(report)
    return tuple(reports)


def _parse_decimal(text: str | None) -> float | None:
    if not text:
        return None
    value = str(text).strip().replace(" ", "")
    if not value:
        return None

    # Türkçe/Avrupa biçimi: 1.234,50 -> 1234.50
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    else:
        # 1,234 yok; yalnız noktalı ondalık veya binlik olabilir. Finansal hedef
        # fiyatlarda iki/üç haneli kesir yaygın olduğu için doğrudan float denenir.
        if value.count(".") > 1:
            value = value.replace(".", "")
    try:
        return float(value)
    except ValueError:
        return None


def _clean_evidence(line: str, *, limit: int = 260) -> str:
    compact = " ".join(str(line).split())
    return compact if len(compact) <= limit else compact[: limit - 1].rstrip() + "…"


def _first_symbol(line: str) -> str | None:
    for match in _SYMBOL_RE.finditer(line.upper()):
        symbol = match.group(1).upper()
        if symbol in _EXCLUDED_SYMBOLS:
            continue
        return symbol
    return None


def _view_from_line(line: str) -> str | None:
    match = _VIEW_RE.search(line)
    if not match:
        # Uzun kurum dili yalnız açık kalıp varsa kabul edilir; serbest yorum yoktur.
        upper = line.upper()
        if "ENDEKS ÜSTÜ GETİRİ" in upper or "ENDEKS USTU GETIRI" in upper:
            return "ENDEKS ÜSTÜ GETİRİ"
        if "ENDEKS ALTI GETİRİ" in upper or "ENDEKS ALTI GETIRI" in upper:
            return "ENDEKS ALTI GETİRİ"
        return None
    return _VIEW_LABELS.get(match.group(1).upper(), match.group(1).upper())


def _target_from_line(line: str) -> float | None:
    match = _TARGET_RE.search(line)
    return _parse_decimal(match.group(1)) if match else None


def _potential_from_line(line: str) -> float | None:
    match = _POTENTIAL_RE.search(line)
    return _parse_decimal(match.group(1)) if match else None


def extract_source_recommendations(
    reports: Iterable[ProcessedMarketReport],
) -> tuple[SourceRecommendation, ...]:
    """Kaynakta AÇIKÇA yazılı kurum görüşlerini çıkarır.

    Bu fonksiyon karar üretmez. `alım`, geri alım, pay alımı gibi normal haber
    ifadelerinden AL/SAT sonucu türetmez; yalnız bağımsız AL/TUT/SAT/NÖTR veya
    açık endeks-göreli tavsiye kalıbı bulunan satırlar kabul edilir.
    """

    recommendations: list[SourceRecommendation] = []
    seen: set[tuple[object, ...]] = set()

    for report in reports:
        for raw_line in report.raw_text.splitlines():
            line = " ".join(raw_line.split())
            if not line:
                continue

            view = _view_from_line(line)
            if not view:
                continue
            symbol = _first_symbol(line)
            if not symbol:
                continue

            target_price = _target_from_line(line)
            potential_percent = _potential_from_line(line)
            evidence = _clean_evidence(line)
            key = (
                report.source.casefold(),
                symbol,
                view,
                target_price,
                potential_percent,
                evidence.casefold(),
            )
            if key in seen:
                continue
            seen.add(key)
            recommendations.append(
                SourceRecommendation(
                    source=report.source,
                    symbol=symbol,
                    source_view=view,
                    target_price=target_price,
                    potential_percent=potential_percent,
                    evidence=evidence,
                    report_id=report.report_id,
                )
            )

    return tuple(recommendations)


def build_daily_market_briefing_snapshot(
    project_root: str | Path,
    review_date: object,
) -> DailyMarketBriefingSnapshot:
    day = normalize_review_date(review_date)
    reports = load_processed_reports(project_root, day)
    return DailyMarketBriefingSnapshot(
        review_date=day,
        reports=reports,
        recommendations=extract_source_recommendations(reports),
    )


def coverage_rows(snapshot: DailyMarketBriefingSnapshot) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for index, report in enumerate(snapshot.reports, start=1):
        rows.append(
            {
                "No": index,
                "Kaynak": report.source,
                "Tür": report.report_type,
                "Tarih": report.report_date,
                "Karakter": report.character_count,
                "Kayıt": report.report_id,
            }
        )
    return tuple(rows)


def recommendation_rows(
    snapshot: DailyMarketBriefingSnapshot,
) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for item in snapshot.recommendations:
        rows.append(
            {
                "Kaynak": item.source,
                "Hisse": item.symbol,
                "Kaynak görüşü": item.source_view,
                "Hedef fiyat": item.target_price,
                "Potansiyel (%)": item.potential_percent,
                "Kaynak satırı": item.evidence,
            }
        )
    return tuple(rows)
