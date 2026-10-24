from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
import csv
import io
import json
from pathlib import Path
from statistics import median
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .shadow_portfolio import CLOSED_STATUS, OPEN_STATUS, ShadowPosition


class WeeklyPerformanceReportError(ValueError):
    """Haftalık performans raporu üretilemedi."""


@dataclass(frozen=True)
class WeeklyPerformanceReport:
    period_start: date
    period_end: date
    opened_count: int
    closed_count: int
    open_count: int
    winning_count: int
    losing_count: int
    flat_count: int
    realized_pnl: float
    unrealized_pnl: float
    average_return_percent: float | None
    median_return_percent: float | None
    best_symbol: str
    best_return_percent: float | None
    worst_symbol: str
    worst_return_percent: float | None
    average_mfe_percent: float | None
    average_mae_percent: float | None
    target_1_hit_rate: float | None
    target_2_hit_rate: float | None
    stop_hit_rate: float | None
    signal_class_rows: tuple[tuple[str, int, float, float], ...]
    quality_band_rows: tuple[tuple[str, int, float, float], ...]
    direction_rows: tuple[tuple[str, int, float, float], ...]
    regime_rows: tuple[tuple[str, int, float, float], ...]
    sector_rows: tuple[tuple[str, int, float, float], ...]
    position_rows: tuple[tuple[object, ...], ...]
    generated_at: datetime
    disclaimer: str = (
        "Bu rapor yalnızca gölge portföy kalibrasyonu ve performans "
        "ölçümü içindir; yatırım danışmanlığı veya alım/satım tavsiyesi değildir."
    )


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _rate(flags: list[bool]) -> float | None:
    return sum(flags) / len(flags) * 100.0 if flags else None


def _quality_band(score: int | None) -> str:
    if score is None:
        return "Bilinmiyor"
    if score >= 80:
        return "80-100"
    if score >= 60:
        return "60-79"
    if score >= 40:
        return "40-59"
    return "0-39"


def _direction_label(position: ShadowPosition) -> str:
    # ShadowPosition günlük/haftalık yönü doğrudan saklamaz.
    # Sinyal sınıfı boş değilse kayıt zincirinin korunduğunu gösterir;
    # ayrıntılı yön verisi bulunmadığında açıkça Bilinmiyor döndürülür.
    return "Bilinmiyor"


def _group_rows(
    positions: Iterable[ShadowPosition],
    key_func,
) -> tuple[tuple[str, int, float, float], ...]:
    groups: dict[str, list[ShadowPosition]] = {}
    for item in positions:
        key = str(key_func(item) or "Bilinmiyor").strip() or "Bilinmiyor"
        groups.setdefault(key, []).append(item)

    rows = []
    for key, items in groups.items():
        returns = [float(item.return_percent) for item in items]
        winners = sum(value > 0 for value in returns)
        rows.append(
            (
                key,
                len(items),
                round(winners / len(items) * 100.0, 2),
                round(sum(returns) / len(returns), 4),
            )
        )
    return tuple(sorted(rows, key=lambda row: (-row[1], row[0])))


def build_weekly_performance_report(
    positions: Iterable[ShadowPosition],
    *,
    period_end: date | None = None,
    days: int = 7,
    generated_at: datetime | None = None,
) -> WeeklyPerformanceReport:
    if days < 1:
        raise WeeklyPerformanceReportError("Rapor dönemi en az 1 gün olmalıdır.")

    resolved_end = period_end or date.today()
    period_start = resolved_end - timedelta(days=days - 1)
    all_positions = tuple(positions)

    opened = tuple(
        item
        for item in all_positions
        if period_start <= item.entry_date <= resolved_end
    )
    closed = tuple(
        item
        for item in all_positions
        if item.status == CLOSED_STATUS
        and item.exit_date is not None
        and period_start <= item.exit_date <= resolved_end
    )
    open_positions = tuple(
        item for item in all_positions if item.status == OPEN_STATUS
    )

    evaluated: list[ShadowPosition] = list(closed)
    for item in open_positions:
        if item.entry_date <= resolved_end:
            evaluated.append(item)

    returns = [float(item.return_percent) for item in evaluated]
    winners = sum(value > 0 for value in returns)
    losers = sum(value < 0 for value in returns)
    flats = sum(value == 0 for value in returns)

    ordered = sorted(
        evaluated,
        key=lambda item: item.return_percent,
    )
    worst = ordered[0] if ordered else None
    best = ordered[-1] if ordered else None

    mfe_values = [
        float(item.mfe_percent)
        for item in evaluated
        if item.mfe_percent is not None
    ]
    mae_values = [
        float(item.mae_percent)
        for item in evaluated
        if item.mae_percent is not None
    ]
    target1_flags = [
        bool(item.target_1_hit)
        for item in evaluated
        if item.target_1 is not None
    ]
    target2_flags = [
        bool(item.target_2_hit)
        for item in evaluated
        if item.target_2 is not None
    ]
    stop_flags = [
        bool(item.stop_hit)
        for item in evaluated
        if item.stop_loss is not None
    ]

    detailed_rows = tuple(
        (
            item.status,
            item.symbol,
            item.entry_date.isoformat(),
            item.exit_date.isoformat() if item.exit_date else "",
            round(item.entry_price, 4),
            round(item.current_price, 4),
            item.quantity,
            round(item.realized_pnl, 2),
            round(item.unrealized_pnl, 2),
            round(item.return_percent, 4),
            item.mfe_percent,
            item.mae_percent,
            item.signal_class or "Bilinmiyor",
            item.quality_score if item.quality_score is not None else "",
            item.market_regime or "Bilinmiyor",
            item.sector or "Bilinmiyor",
            item.close_reason,
        )
        for item in sorted(
            evaluated,
            key=lambda value: (value.entry_date, value.symbol),
            reverse=True,
        )
    )

    return WeeklyPerformanceReport(
        period_start=period_start,
        period_end=resolved_end,
        opened_count=len(opened),
        closed_count=len(closed),
        open_count=len(open_positions),
        winning_count=winners,
        losing_count=losers,
        flat_count=flats,
        realized_pnl=round(sum(item.realized_pnl for item in closed), 2),
        unrealized_pnl=round(
            sum(item.unrealized_pnl for item in open_positions), 2
        ),
        average_return_percent=(
            round(_average(returns), 4) if returns else None
        ),
        median_return_percent=(
            round(float(median(returns)), 4) if returns else None
        ),
        best_symbol=best.symbol if best else "",
        best_return_percent=(
            round(best.return_percent, 4) if best else None
        ),
        worst_symbol=worst.symbol if worst else "",
        worst_return_percent=(
            round(worst.return_percent, 4) if worst else None
        ),
        average_mfe_percent=(
            round(_average(mfe_values), 4) if mfe_values else None
        ),
        average_mae_percent=(
            round(_average(mae_values), 4) if mae_values else None
        ),
        target_1_hit_rate=(
            round(_rate(target1_flags), 2) if target1_flags else None
        ),
        target_2_hit_rate=(
            round(_rate(target2_flags), 2) if target2_flags else None
        ),
        stop_hit_rate=(
            round(_rate(stop_flags), 2) if stop_flags else None
        ),
        signal_class_rows=_group_rows(
            evaluated, lambda item: item.signal_class
        ),
        quality_band_rows=_group_rows(
            evaluated, lambda item: _quality_band(item.quality_score)
        ),
        direction_rows=_group_rows(evaluated, _direction_label),
        regime_rows=_group_rows(
            evaluated, lambda item: item.market_regime
        ),
        sector_rows=_group_rows(evaluated, lambda item: item.sector),
        position_rows=detailed_rows,
        generated_at=generated_at or datetime.now(timezone.utc),
    )


def summary_rows(report: WeeklyPerformanceReport) -> list[dict[str, object]]:
    def value_or_dash(value: object) -> object:
        return "-" if value is None or value == "" else value

    return [
        {"Gösterge": "Dönem", "Değer": f"{report.period_start} - {report.period_end}"},
        {"Gösterge": "Açılan pozisyon", "Değer": report.opened_count},
        {"Gösterge": "Kapanan pozisyon", "Değer": report.closed_count},
        {"Gösterge": "Açık pozisyon", "Değer": report.open_count},
        {"Gösterge": "Kazanan", "Değer": report.winning_count},
        {"Gösterge": "Kaybeden", "Değer": report.losing_count},
        {"Gösterge": "Başa baş", "Değer": report.flat_count},
        {"Gösterge": "Gerçekleşen K/Z", "Değer": report.realized_pnl},
        {"Gösterge": "Gerçekleşmemiş K/Z", "Değer": report.unrealized_pnl},
        {"Gösterge": "Ortalama getiri (%)", "Değer": value_or_dash(report.average_return_percent)},
        {"Gösterge": "Medyan getiri (%)", "Değer": value_or_dash(report.median_return_percent)},
        {"Gösterge": "En iyi işlem", "Değer": f"{report.best_symbol} · {value_or_dash(report.best_return_percent)}"},
        {"Gösterge": "En kötü işlem", "Değer": f"{report.worst_symbol} · {value_or_dash(report.worst_return_percent)}"},
        {"Gösterge": "Ortalama MFE (%)", "Değer": value_or_dash(report.average_mfe_percent)},
        {"Gösterge": "Ortalama MAE (%)", "Değer": value_or_dash(report.average_mae_percent)},
        {"Gösterge": "Hedef 1 oranı (%)", "Değer": value_or_dash(report.target_1_hit_rate)},
        {"Gösterge": "Hedef 2 oranı (%)", "Değer": value_or_dash(report.target_2_hit_rate)},
        {"Gösterge": "Stop oranı (%)", "Değer": value_or_dash(report.stop_hit_rate)},
    ]


def group_rows_for_table(
    rows: Iterable[tuple[str, int, float, float]],
) -> list[dict[str, object]]:
    return [
        {
            "Grup": key,
            "İşlem": count,
            "Başarı (%)": success_rate,
            "Ortalama getiri (%)": average_return,
        }
        for key, count, success_rate, average_return in rows
    ]


def weekly_report_csv_bytes(report: WeeklyPerformanceReport) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("Bölüm", "Gösterge", "Değer", "Ek 1", "Ek 2"))

    for row in summary_rows(report):
        writer.writerow(("Özet", row["Gösterge"], row["Değer"], "", ""))

    for title, rows in (
        ("Sinyal sınıfı", report.signal_class_rows),
        ("Kalite bandı", report.quality_band_rows),
        ("Günlük/haftalık yön", report.direction_rows),
        ("Piyasa rejimi", report.regime_rows),
        ("Sektör", report.sector_rows),
    ):
        for key, count, success_rate, avg_return in rows:
            writer.writerow(
                (title, key, count, success_rate, avg_return)
            )

    writer.writerow(())
    writer.writerow(
        (
            "Durum", "Sembol", "Giriş tarihi", "Çıkış tarihi",
            "Giriş fiyatı", "Son/çıkış fiyatı", "Lot",
            "Gerçekleşen K/Z", "Gerçekleşmemiş K/Z", "Getiri (%)",
            "MFE (%)", "MAE (%)", "Sinyal sınıfı", "Kalite",
            "Rejim", "Sektör", "Kapanış nedeni",
        )
    )
    writer.writerows(report.position_rows)
    writer.writerow(())
    writer.writerow(("Yasal uyarı", report.disclaimer))
    return output.getvalue().encode("utf-8-sig")


def _register_font() -> str:
    candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    )
    for path in candidates:
        if path.exists():
            name = "WeeklyPerformanceUnicode"
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(path)))
            return name
    return "Helvetica"


def _pdf_text(value: object, font_name: str) -> str:
    text = str(value)
    if font_name != "Helvetica":
        return text
    return text.translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU"))


def _table(rows, font_name: str, widths=None) -> Table:
    data = [
        [_pdf_text(value, font_name) for value in row]
        for row in rows
    ]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            (
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF3")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9CA3AF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            )
        )
    )
    return table


def weekly_report_pdf_bytes(report: WeeklyPerformanceReport) -> bytes:
    buffer = io.BytesIO()
    font = _register_font()
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "WeeklyTitle",
        parent=styles["Title"],
        fontName=font,
        fontSize=15,
        leading=18,
        spaceAfter=7,
    )
    heading = ParagraphStyle(
        "WeeklyHeading",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=10,
        leading=12,
        spaceBefore=6,
        spaceAfter=4,
    )
    normal = ParagraphStyle(
        "WeeklyNormal",
        parent=styles["BodyText"],
        fontName=font,
        fontSize=8,
        leading=10,
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Hisse Robotu Haftalık Performans Raporu",
    )
    story = [
        Paragraph(
            _pdf_text("Hisse Robotu - Haftalık Performans Raporu", font),
            title,
        ),
        Paragraph(
            _pdf_text(
                f"Dönem: {report.period_start} - {report.period_end}",
                font,
            ),
            normal,
        ),
        Spacer(1, 4),
        Paragraph(_pdf_text("Özet", font), heading),
        _table(
            [["Gösterge", "Değer"]]
            + [[row["Gösterge"], row["Değer"]] for row in summary_rows(report)],
            font,
            widths=(70 * mm, 55 * mm),
        ),
    ]

    for title_text, rows in (
        ("Sinyal sınıfı", report.signal_class_rows),
        ("Kalite skoru bandı", report.quality_band_rows),
        ("Günlük/haftalık yön uyumu", report.direction_rows),
        ("Piyasa rejimi", report.regime_rows),
        ("Sektör", report.sector_rows),
    ):
        story.extend(
            (
                Paragraph(_pdf_text(title_text, font), heading),
                _table(
                    [["Grup", "İşlem", "Başarı (%)", "Ort. getiri (%)"]]
                    + [list(row) for row in rows],
                    font,
                    widths=(70 * mm, 25 * mm, 30 * mm, 35 * mm),
                ),
            )
        )

    if report.position_rows:
        story.extend(
            (
                Paragraph(_pdf_text("İşlem ayrıntıları", font), heading),
                _table(
                    [[
                        "Durum", "Sembol", "Giriş", "Çıkış",
                        "Giriş F.", "Son F.", "Lot", "Getiri %",
                        "MFE %", "MAE %", "Sınıf", "Kalite",
                        "Rejim", "Sektör",
                    ]]
                    + [
                        [
                            row[0], row[1], row[2], row[3], row[4], row[5],
                            row[6], row[9], row[10], row[11], row[12],
                            row[13], row[14], row[15],
                        ]
                        for row in report.position_rows
                    ],
                    font,
                ),
            )
        )

    story.extend(
        (
            Spacer(1, 6),
            Paragraph(_pdf_text(report.disclaimer, font), normal),
            Paragraph(
                _pdf_text(
                    f"Üretim zamanı: {report.generated_at.isoformat()}",
                    font,
                ),
                normal,
            ),
        )
    )
    doc.build(story)
    return buffer.getvalue()


class WeeklyPerformanceArchive:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = (
            Path(root).expanduser()
            if root is not None
            else Path.home() / ".hisse_robotu" / "haftalik_raporlar"
        )

    def save(
        self,
        report: WeeklyPerformanceReport,
        *,
        csv_bytes: bytes,
        pdf_bytes: bytes,
    ) -> tuple[Path, Path, Path]:
        self.root.mkdir(parents=True, exist_ok=True)
        key = f"{report.period_start}_{report.period_end}"
        csv_path = self.root / f"haftalik_performans_{key}.csv"
        pdf_path = self.root / f"haftalik_performans_{key}.pdf"
        json_path = self.root / f"haftalik_performans_{key}.json"
        csv_path.write_bytes(csv_bytes)
        pdf_path.write_bytes(pdf_bytes)
        json_path.write_text(
            json.dumps(
                {
                    **asdict(report),
                    "period_start": report.period_start.isoformat(),
                    "period_end": report.period_end.isoformat(),
                    "generated_at": report.generated_at.isoformat(),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        return csv_path, pdf_path, json_path

    def list(self) -> tuple[Path, ...]:
        if not self.root.exists():
            return ()
        return tuple(
            sorted(
                self.root.glob("haftalik_performans_*.json"),
                reverse=True,
            )
        )
