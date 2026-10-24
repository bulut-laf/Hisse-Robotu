from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Literal

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors

from .fundamental_report import FundamentalReport


class FundamentalReportArchiveError(ValueError):
    """Temel analiz rapor arşivi işlemi başarısız oldu."""


@dataclass(frozen=True)
class ArchivedFundamentalReport:
    report_id: str
    data_identity: str
    symbol: str
    period_key: str
    period_end: date
    created_at: datetime
    report: FundamentalReport


@dataclass(frozen=True)
class FundamentalReportArchiveSaveResult:
    inserted: int
    unchanged: int
    archived: ArchivedFundamentalReport


@dataclass(frozen=True)
class FundamentalReportComparison:
    symbol: str
    previous_period: str
    current_period: str
    total_score_change: int | None
    component_changes: tuple[tuple[str, int], ...]
    ratio_changes: tuple[tuple[str, str, str], ...]
    sector_ranking_change: tuple[str, str]
    sector_strength_change: tuple[str, str]
    source_change: tuple[str, str]
    freshness_change: tuple[str, str]


def _json_default(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"JSON'a çevrilemeyen değer: {type(value)!r}")


def _report_payload(report: FundamentalReport) -> dict[str, Any]:
    payload = asdict(report)
    payload["period_end"] = report.period_end.isoformat()
    payload["generated_at"] = report.generated_at.astimezone(
        timezone.utc
    ).isoformat()
    return payload


def _data_identity(report: FundamentalReport) -> str:
    payload = _report_payload(report)
    payload.pop("generated_at", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=_json_default,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _report_from_payload(payload: dict[str, Any]) -> FundamentalReport:
    return FundamentalReport(
        symbol=str(payload["symbol"]),
        period_key=str(payload["period_key"]),
        period_end=date.fromisoformat(str(payload["period_end"])),
        currency=str(payload["currency"]),
        source=str(payload["source"]),
        freshness_status=str(payload["freshness_status"]),
        age_days=(
            int(payload["age_days"])
            if payload.get("age_days") is not None
            else None
        ),
        total_score=(
            int(payload["total_score"])
            if payload.get("total_score") is not None
            else None
        ),
        grade=str(payload["grade"]),
        component_scores=tuple(
            (str(name), int(score), int(maximum))
            for name, score, maximum
            in payload.get("component_scores", ())
        ),
        score_change=str(payload["score_change"]),
        ratio_rows=tuple(
            (str(metric), str(value))
            for metric, value in payload.get("ratio_rows", ())
        ),
        sector_ratio_rows=tuple(
            (
                str(metric),
                str(company),
                str(sector_median),
                str(position),
            )
            for metric, company, sector_median, position
            in payload.get("sector_ratio_rows", ())
        ),
        sector_ranking=str(payload["sector_ranking"]),
        sector_strength=str(payload["sector_strength"]),
        quality_flags=tuple(
            str(flag) for flag in payload.get("quality_flags", ())
        ),
        generated_at=datetime.fromisoformat(
            str(payload["generated_at"])
        ),
        disclaimer=str(payload.get("disclaimer", "")),
    )


class FundamentalReportJsonArchive:
    def __init__(
        self,
        path: Path | str = Path(
            "backend/data/fundamental_report_archive.json"
        ),
    ) -> None:
        self.path = Path(path)

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FundamentalReportArchiveError(
                "Temel rapor arşivi okunamadı."
            ) from exc
        if not isinstance(raw, list):
            raise FundamentalReportArchiveError(
                "Temel rapor arşiv biçimi geçersiz."
            )
        return raw

    def _write(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(
                records,
                ensure_ascii=False,
                indent=2,
                default=_json_default,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _to_archived(
        record: dict[str, Any],
    ) -> ArchivedFundamentalReport:
        try:
            report = _report_from_payload(record["report"])
            return ArchivedFundamentalReport(
                report_id=str(record["report_id"]),
                data_identity=str(record["data_identity"]),
                symbol=str(record["symbol"]).upper(),
                period_key=str(record["period_key"]),
                period_end=date.fromisoformat(
                    str(record["period_end"])
                ),
                created_at=datetime.fromisoformat(
                    str(record["created_at"])
                ),
                report=report,
            )
        except Exception as exc:
            raise FundamentalReportArchiveError(
                "Arşivde geçersiz temel rapor kaydı bulundu."
            ) from exc

    def save(
        self,
        report: FundamentalReport,
    ) -> FundamentalReportArchiveSaveResult:
        identity = _data_identity(report)
        records = self._read()

        for record in records:
            if (
                str(record.get("symbol", "")).upper()
                == report.symbol.upper()
                and str(record.get("data_identity", ""))
                == identity
            ):
                archived = self._to_archived(record)
                return FundamentalReportArchiveSaveResult(
                    inserted=0,
                    unchanged=1,
                    archived=archived,
                )

        created_at = datetime.now(timezone.utc)
        report_id = (
            f"{report.symbol.upper()}-{report.period_key}-"
            f"{created_at.strftime('%Y%m%dT%H%M%S%fZ')}"
        )
        record = {
            "report_id": report_id,
            "data_identity": identity,
            "symbol": report.symbol.upper(),
            "period_key": report.period_key,
            "period_end": report.period_end.isoformat(),
            "created_at": created_at.isoformat(),
            "report": _report_payload(report),
        }
        records.append(record)
        self._write(records)

        return FundamentalReportArchiveSaveResult(
            inserted=1,
            unchanged=0,
            archived=self._to_archived(record),
        )

    def list_all(
        self,
        *,
        maximum_age_days: int = 1095,
        today: date | None = None,
    ) -> tuple[ArchivedFundamentalReport, ...]:
        if maximum_age_days < 1:
            raise FundamentalReportArchiveError(
                "Azami rapor yaşı en az 1 gün olmalıdır."
            )

        reference = today or date.today()
        items: list[ArchivedFundamentalReport] = []
        for record in self._read():
            archived = self._to_archived(record)
            age_days = (reference - archived.period_end).days
            if age_days < 0 or age_days > maximum_age_days:
                continue
            items.append(archived)

        return tuple(
            sorted(
                items,
                key=lambda item: (
                    item.period_end,
                    item.created_at,
                    item.symbol,
                ),
                reverse=True,
            )
        )

    def list_symbol(
        self,
        symbol: str,
        *,
        maximum_age_days: int = 1095,
        today: date | None = None,
    ) -> tuple[ArchivedFundamentalReport, ...]:
        normalized = symbol.strip().upper()
        if not normalized:
            raise FundamentalReportArchiveError(
                "Şirket sembolü boş olamaz."
            )
        if maximum_age_days < 1:
            raise FundamentalReportArchiveError(
                "Azami rapor yaşı en az 1 gün olmalıdır."
            )

        reference = today or date.today()
        items = []
        for record in self._read():
            if str(record.get("symbol", "")).upper() != normalized:
                continue
            archived = self._to_archived(record)
            age_days = (reference - archived.period_end).days
            if age_days < 0 or age_days > maximum_age_days:
                continue
            items.append(archived)

        return tuple(
            sorted(
                items,
                key=lambda item: (
                    item.period_end,
                    item.created_at,
                ),
                reverse=True,
            )
        )


def compare_archived_reports(
    previous: ArchivedFundamentalReport,
    current: ArchivedFundamentalReport,
) -> FundamentalReportComparison:
    if previous.symbol != current.symbol:
        raise FundamentalReportArchiveError(
            "Yalnızca aynı şirkete ait raporlar karşılaştırılabilir."
        )
    if previous.period_end > current.period_end:
        raise FundamentalReportArchiveError(
            "Önceki rapor güncel rapordan daha yeni olamaz."
        )
    if previous.report.currency != current.report.currency:
        raise FundamentalReportArchiveError(
            "Farklı para birimindeki raporlar karşılaştırılamaz."
        )

    old_total = previous.report.total_score
    new_total = current.report.total_score
    total_change = (
        new_total - old_total
        if old_total is not None and new_total is not None
        else None
    )

    old_components = {
        name: score
        for name, score, _ in previous.report.component_scores
    }
    new_components = {
        name: score
        for name, score, _ in current.report.component_scores
    }
    common_components = sorted(
        set(old_components) & set(new_components)
    )
    component_changes = tuple(
        (
            name,
            new_components[name] - old_components[name],
        )
        for name in common_components
    )

    old_ratios = dict(previous.report.ratio_rows)
    new_ratios = dict(current.report.ratio_rows)
    common_ratios = sorted(set(old_ratios) & set(new_ratios))
    ratio_changes = tuple(
        (
            metric,
            old_ratios[metric],
            new_ratios[metric],
        )
        for metric in common_ratios
        if old_ratios[metric] != new_ratios[metric]
    )

    return FundamentalReportComparison(
        symbol=current.symbol,
        previous_period=previous.period_key,
        current_period=current.period_key,
        total_score_change=total_change,
        component_changes=component_changes,
        ratio_changes=ratio_changes,
        sector_ranking_change=(
            previous.report.sector_ranking,
            current.report.sector_ranking,
        ),
        sector_strength_change=(
            previous.report.sector_strength,
            current.report.sector_strength,
        ),
        source_change=(
            previous.report.source,
            current.report.source,
        ),
        freshness_change=(
            previous.report.freshness_status,
            current.report.freshness_status,
        ),
    )


def report_archive_rows(
    reports: Iterable[ArchivedFundamentalReport],
) -> list[dict[str, object]]:
    return [
        {
            "Rapor kimliği": item.report_id,
            "Şirket": item.symbol,
            "Dönem": item.period_key,
            "Dönem sonu": item.period_end,
            "Temel skor": item.report.total_score,
            "Kalite sınıfı": item.report.grade,
            "Kaynak": item.report.source,
            "Tazelik": item.report.freshness_status,
            "Oluşturulma": item.created_at,
        }
        for item in reports
    ]


def report_comparison_rows(
    comparison: FundamentalReportComparison,
) -> list[dict[str, object]]:
    rows = [
        {
            "Gösterge": "Toplam temel skor değişimi",
            "Önceki": comparison.previous_period,
            "Güncel": comparison.current_period,
            "Değişim": comparison.total_score_change,
        }
    ]
    rows.extend(
        {
            "Gösterge": name,
            "Önceki": "",
            "Güncel": "",
            "Değişim": change,
        }
        for name, change in comparison.component_changes
    )
    rows.extend(
        {
            "Gösterge": metric,
            "Önceki": previous,
            "Güncel": current,
            "Değişim": "Metinsel oran değişimi",
        }
        for metric, previous, current in comparison.ratio_changes
    )
    rows.extend(
        (
            {
                "Gösterge": "Sektör sıralaması",
                "Önceki": comparison.sector_ranking_change[0],
                "Güncel": comparison.sector_ranking_change[1],
                "Değişim": "",
            },
            {
                "Gösterge": "Sektör güç haritası",
                "Önceki": comparison.sector_strength_change[0],
                "Güncel": comparison.sector_strength_change[1],
                "Değişim": "",
            },
            {
                "Gösterge": "Veri kaynağı",
                "Önceki": comparison.source_change[0],
                "Güncel": comparison.source_change[1],
                "Değişim": "",
            },
            {
                "Gösterge": "Tazelik",
                "Önceki": comparison.freshness_change[0],
                "Güncel": comparison.freshness_change[1],
                "Değişim": "",
            },
        )
    )
    return rows

ArchiveSortField = Literal[
    "period_desc",
    "period_asc",
    "created_desc",
    "created_asc",
    "score_desc",
    "score_asc",
]


@dataclass(frozen=True)
class FundamentalReportArchiveFilter:
    symbol_query: str = ""
    period_start: date | None = None
    period_end: date | None = None
    minimum_score: int | None = None
    maximum_score: int | None = None
    grades: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    freshness_statuses: tuple[str, ...] = ()
    sort_by: ArchiveSortField = "period_desc"

    def __post_init__(self) -> None:
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_start > self.period_end
        ):
            raise FundamentalReportArchiveError(
                "Dönem başlangıcı dönem bitişinden sonra olamaz."
            )
        for name, value in (
            ("Asgari skor", self.minimum_score),
            ("Azami skor", self.maximum_score),
        ):
            if value is not None and not 0 <= value <= 100:
                raise FundamentalReportArchiveError(
                    f"{name} 0–100 aralığında olmalıdır."
                )
        if (
            self.minimum_score is not None
            and self.maximum_score is not None
            and self.minimum_score > self.maximum_score
        ):
            raise FundamentalReportArchiveError(
                "Asgari skor azami skordan büyük olamaz."
            )
        valid_sorts = {
            "period_desc",
            "period_asc",
            "created_desc",
            "created_asc",
            "score_desc",
            "score_asc",
        }
        if self.sort_by not in valid_sorts:
            raise FundamentalReportArchiveError(
                "Arşiv sıralama alanı geçersiz."
            )


def _archive_sort_key(
    item: ArchivedFundamentalReport,
    sort_by: ArchiveSortField,
) -> tuple[object, ...]:
    score = (
        item.report.total_score
        if item.report.total_score is not None
        else -1
    )
    if sort_by == "period_asc":
        return (item.period_end, item.created_at, item.symbol)
    if sort_by == "created_desc":
        return (-item.created_at.timestamp(), item.symbol)
    if sort_by == "created_asc":
        return (item.created_at.timestamp(), item.symbol)
    if sort_by == "score_desc":
        return (-score, -item.period_end.toordinal(), item.symbol)
    if sort_by == "score_asc":
        return (score, item.period_end.toordinal(), item.symbol)
    return (-item.period_end.toordinal(), -item.created_at.timestamp(), item.symbol)


def search_archived_reports(
    reports: Iterable[ArchivedFundamentalReport],
    filters: FundamentalReportArchiveFilter,
) -> tuple[ArchivedFundamentalReport, ...]:
    symbol_query = filters.symbol_query.strip().upper()
    grades = {value.strip() for value in filters.grades if value.strip()}
    sources = {value.strip() for value in filters.sources if value.strip()}
    freshness = {
        value.strip()
        for value in filters.freshness_statuses
        if value.strip()
    }

    result: list[ArchivedFundamentalReport] = []
    for item in reports:
        if symbol_query and symbol_query not in item.symbol:
            continue
        if (
            filters.period_start is not None
            and item.period_end < filters.period_start
        ):
            continue
        if (
            filters.period_end is not None
            and item.period_end > filters.period_end
        ):
            continue

        score = item.report.total_score
        if filters.minimum_score is not None:
            if score is None or score < filters.minimum_score:
                continue
        if filters.maximum_score is not None:
            if score is None or score > filters.maximum_score:
                continue

        if grades and item.report.grade not in grades:
            continue
        if sources and item.report.source not in sources:
            continue
        if (
            freshness
            and item.report.freshness_status not in freshness
        ):
            continue

        result.append(item)

    return tuple(
        sorted(
            result,
            key=lambda item: _archive_sort_key(
                item,
                filters.sort_by,
            ),
        )
    )


def archived_reports_csv_bytes(
    reports: Iterable[ArchivedFundamentalReport],
) -> bytes:
    items = tuple(reports)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        (
            "report_id",
            "symbol",
            "period_key",
            "period_end",
            "total_score",
            "grade",
            "source",
            "freshness_status",
            "created_at",
        )
    )
    for item in items:
        writer.writerow(
            (
                item.report_id,
                item.symbol,
                item.period_key,
                item.period_end.isoformat(),
                item.report.total_score,
                item.report.grade,
                item.report.source,
                item.report.freshness_status,
                item.created_at.isoformat(),
            )
        )
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def archived_reports_pdf_bytes(
    reports: Iterable[ArchivedFundamentalReport],
) -> bytes:
    items = tuple(reports)
    if not items:
        raise FundamentalReportArchiveError(
            "Toplu PDF için en az bir rapor seçilmelidir."
        )

    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Temel Analiz Rapor Arşivi",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Temel Analiz Rapor Arşivi", styles["Title"]),
        Spacer(1, 5 * mm),
        Paragraph(
            (
                "Bu toplu özet bilgilendirme amaçlıdır; "
                "yatırım danışmanlığı veya alım/satım "
                "tavsiyesi değildir."
            ),
            styles["BodyText"],
        ),
        Spacer(1, 5 * mm),
    ]

    for index, item in enumerate(items):
        if index:
            story.append(PageBreak())
        report = item.report
        story.append(
            Paragraph(
                f"{item.symbol} · {item.period_key}",
                styles["Heading1"],
            )
        )
        data = [
            ["Gösterge", "Değer"],
            ["Rapor kimliği", item.report_id],
            ["Dönem sonu", item.period_end.isoformat()],
            ["Temel skor", str(report.total_score or "Veri yok")],
            ["Kalite sınıfı", report.grade],
            ["Kaynak", report.source],
            ["Tazelik", report.freshness_status],
            ["Sektör sıralaması", report.sector_ranking],
            ["Sektör gücü", report.sector_strength],
        ]
        table = Table(data, colWidths=(58 * mm, 104 * mm))
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(report.disclaimer, styles["BodyText"]))

    document.build(story)
    return output.getvalue()

