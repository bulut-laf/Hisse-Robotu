from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class FundamentalReportError(ValueError):
    """Temel analiz raporu üretilemedi."""


@dataclass(frozen=True)
class FundamentalReport:
    symbol: str
    period_key: str
    period_end: date
    currency: str
    source: str
    freshness_status: str
    age_days: int | None
    total_score: int | None
    grade: str
    component_scores: tuple[tuple[str, int, int], ...]
    score_change: str
    ratio_rows: tuple[tuple[str, str], ...]
    sector_ratio_rows: tuple[tuple[str, str, str, str], ...]
    sector_ranking: str
    sector_strength: str
    quality_flags: tuple[str, ...]
    generated_at: datetime
    disclaimer: str = (
        "Bu rapor bilgilendirme amaçlıdır; yatırım danışmanlığı "
        "veya alım/satım tavsiyesi değildir."
    )

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise FundamentalReportError("Şirket sembolü boş olamaz.")
        if not self.period_key.strip():
            raise FundamentalReportError("Finansal dönem boş olamaz.")
        if not self.currency.strip():
            raise FundamentalReportError("Para birimi boş olamaz.")
        if not self.source.strip():
            raise FundamentalReportError("Veri kaynağı boş olamaz.")
        if self.total_score is not None and not 0 <= self.total_score <= 100:
            raise FundamentalReportError(
                "Temel kalite skoru 0–100 aralığında olmalıdır."
            )


def _value_text(value: object) -> str:
    if value is None:
        return "Veri yok"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def fundamental_report_csv_bytes(
    report: FundamentalReport,
) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(("Bölüm", "Gösterge", "Değer", "Referans", "Konum"))

    summary = (
        ("Şirket", report.symbol),
        ("Dönem", report.period_key),
        ("Dönem sonu", report.period_end.isoformat()),
        ("Para birimi", report.currency),
        ("Kaynak", report.source),
        ("Tazelik", report.freshness_status),
        (
            "Veri yaşı",
            f"{report.age_days} gün"
            if report.age_days is not None
            else "Bilinmiyor",
        ),
        (
            "Temel kalite skoru",
            f"{report.total_score}/100"
            if report.total_score is not None
            else "Hesaplanamadı",
        ),
        ("Kalite sınıfı", report.grade),
        ("Dönemsel skor değişimi", report.score_change),
        ("Sektör sıralaması", report.sector_ranking),
        ("Sektör güç haritası", report.sector_strength),
    )
    for metric, value in summary:
        writer.writerow(("Özet", metric, value, "", ""))

    for name, score, maximum in report.component_scores:
        writer.writerow(
            ("Alt skor", name, f"{score}/{maximum}", "", "")
        )

    for metric, value in report.ratio_rows:
        writer.writerow(("Finansal oran", metric, value, "", ""))

    for metric, company, sector_median, position in report.sector_ratio_rows:
        writer.writerow(
            (
                "Sektör oran karşılaştırması",
                metric,
                company,
                sector_median,
                position,
            )
        )

    if report.quality_flags:
        for flag in report.quality_flags:
            writer.writerow(("Kalite uyarısı", "Uyarı", flag, "", ""))
    else:
        writer.writerow(
            (
                "Kalite uyarısı",
                "Durum",
                "Belirgin kalite uyarısı yok",
                "",
                "",
            )
        )

    writer.writerow(("Yasal uyarı", "Açıklama", report.disclaimer, "", ""))
    writer.writerow(
        (
            "Rapor",
            "Üretim zamanı",
            report.generated_at.astimezone(timezone.utc).isoformat(),
            "",
            "",
        )
    )
    return output.getvalue().encode("utf-8-sig")


def _register_pdf_font() -> str:
    font_candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    )
    for path in font_candidates:
        if path.exists():
            font_name = "FundamentalReportUnicode"
            if font_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(font_name, str(path)))
            return font_name
    return "Helvetica"


def _pdf_text(value: object, font_name: str) -> str:
    text = _value_text(value)
    if font_name != "Helvetica":
        return text
    replacements = str.maketrans(
        "çğıöşüÇĞİÖŞÜ",
        "cgiosuCGIOSU",
    )
    return text.translate(replacements)


def _table(
    rows: Sequence[Sequence[object]],
    *,
    font_name: str,
    column_widths: Sequence[float] | None = None,
) -> Table:
    converted = [
        [_pdf_text(value, font_name) for value in row]
        for row in rows
    ]
    table = Table(
        converted,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            (
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EDF3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9CA3AF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            )
        )
    )
    return table


def fundamental_report_pdf_bytes(
    report: FundamentalReport,
) -> bytes:
    buffer = io.BytesIO()
    font_name = _register_pdf_font()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FundamentalTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=16,
        leading=19,
        spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "FundamentalHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=11,
        leading=14,
        spaceBefore=8,
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "FundamentalBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8,
        leading=11,
    )

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"{report.symbol} Temel Analiz Özeti",
        author="Hisse Robotu",
    )

    story = [
        Paragraph(
            _pdf_text(
                f"{report.symbol} Temel Analiz Özet Raporu",
                font_name,
            ),
            title_style,
        ),
        Paragraph(
            _pdf_text(report.disclaimer, font_name),
            body_style,
        ),
        Spacer(1, 5 * mm),
        Paragraph(_pdf_text("Rapor özeti", font_name), heading_style),
        _table(
            (
                ("Gösterge", "Değer"),
                ("Şirket", report.symbol),
                ("Dönem", report.period_key),
                ("Dönem sonu", report.period_end.isoformat()),
                ("Para birimi", report.currency),
                ("Kaynak", report.source),
                ("Tazelik", report.freshness_status),
                (
                    "Veri yaşı",
                    f"{report.age_days} gün"
                    if report.age_days is not None
                    else "Bilinmiyor",
                ),
                (
                    "Temel kalite skoru",
                    f"{report.total_score}/100"
                    if report.total_score is not None
                    else "Hesaplanamadı",
                ),
                ("Kalite sınıfı", report.grade),
                ("Dönemsel skor değişimi", report.score_change),
            ),
            font_name=font_name,
            column_widths=(55 * mm, 115 * mm),
        ),
        Paragraph(_pdf_text("Alt skorlar", font_name), heading_style),
        _table(
            (
                ("Bileşen", "Skor"),
                *(
                    (name, f"{score}/{maximum}")
                    for name, score, maximum
                    in report.component_scores
                ),
            ),
            font_name=font_name,
            column_widths=(100 * mm, 70 * mm),
        ),
        Paragraph(
            _pdf_text("Finansal oranlar", font_name),
            heading_style,
        ),
        _table(
            (("Gösterge", "Değer"), *report.ratio_rows),
            font_name=font_name,
            column_widths=(100 * mm, 70 * mm),
        ),
    ]

    if report.sector_ratio_rows:
        story.extend(
            (
                Paragraph(
                    _pdf_text(
                        "Sektör medyanı karşılaştırması",
                        font_name,
                    ),
                    heading_style,
                ),
                _table(
                    (
                        (
                            "Finansal oran",
                            "Şirket",
                            "Sektör medyanı",
                            "Konum",
                        ),
                        *report.sector_ratio_rows,
                    ),
                    font_name=font_name,
                    column_widths=(
                        45 * mm,
                        28 * mm,
                        32 * mm,
                        65 * mm,
                    ),
                ),
            )
        )

    story.extend(
        (
            Paragraph(
                _pdf_text("Sektör konumu", font_name),
                heading_style,
            ),
            _table(
                (
                    ("Gösterge", "Değer"),
                    ("Sektör sıralaması", report.sector_ranking),
                    ("Sektör güç haritası", report.sector_strength),
                ),
                font_name=font_name,
                column_widths=(55 * mm, 115 * mm),
            ),
            Paragraph(
                _pdf_text("Finansal kalite uyarıları", font_name),
                heading_style,
            ),
        )
    )

    if report.quality_flags:
        for flag in report.quality_flags:
            story.append(
                Paragraph(
                    _pdf_text(f"• {flag}", font_name),
                    body_style,
                )
            )
    else:
        story.append(
            Paragraph(
                _pdf_text(
                    "Belirgin finansal kalite uyarısı bulunmadı.",
                    font_name,
                ),
                body_style,
            )
        )

    story.extend(
        (
            Spacer(1, 6 * mm),
            Paragraph(
                _pdf_text(
                    "Rapor üretim zamanı (UTC): "
                    + report.generated_at.astimezone(
                        timezone.utc
                    ).isoformat(),
                    font_name,
                ),
                body_style,
            ),
        )
    )

    try:
        document.build(story)
    except Exception as exc:
        raise FundamentalReportError(
            "PDF raporu oluşturulamadı."
        ) from exc

    return buffer.getvalue()


def fundamental_report_file_names(
    report: FundamentalReport,
) -> tuple[str, str]:
    base = (
        f"{report.symbol}_{report.period_key}_temel_analiz_ozeti"
    )
    return f"{base}.csv", f"{base}.pdf"
