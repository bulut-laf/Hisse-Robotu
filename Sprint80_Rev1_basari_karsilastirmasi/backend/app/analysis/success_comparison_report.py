from __future__ import annotations

from dataclasses import dataclass
import csv
import io
import math
from statistics import median
from typing import Callable, Iterable

from .signal_outcome_tracking import SignalOutcome


class SuccessComparisonError(ValueError):
    """Başarı karşılaştırması üretilemedi."""


@dataclass(frozen=True)
class ComparisonRow:
    dimension: str
    group: str
    horizon: int
    sample_count: int
    success_count: int
    success_rate_percent: float
    average_return_percent: float
    median_return_percent: float
    average_mfe_percent: float
    average_mae_percent: float
    target_1_rate_percent: float | None
    target_2_rate_percent: float | None
    stop_rate_percent: float | None
    sample_status: str


@dataclass(frozen=True)
class SuccessComparisonReport:
    rows: tuple[ComparisonRow, ...]
    minimum_sample_size: int
    strongest: tuple[ComparisonRow, ...]
    weakest: tuple[ComparisonRow, ...]


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _rate(values: list[bool]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values) * 100.0


def _quality_band(score: int) -> str:
    if score >= 80:
        return "80–100"
    if score >= 60:
        return "60–79"
    if score >= 40:
        return "40–59"
    return "0–39"


def _direction_alignment(outcome: SignalOutcome) -> str:
    daily = outcome.snapshot.daily_direction.strip().casefold()
    weekly = outcome.snapshot.weekly_direction.strip().casefold()
    if not daily or not weekly:
        return "Belirsiz"
    return "Uyumlu" if daily == weekly else "Uyumsuz"


def _volume_label(value: bool | None) -> str:
    if value is True:
        return "Hacim onaylı"
    if value is False:
        return "Hacim onaysız"
    return "Hacim bilgisi yok"


def _indicator_label(outcome: SignalOutcome) -> str:
    parts = []
    if outcome.snapshot.momentum_state.strip():
        parts.append(outcome.snapshot.momentum_state.strip())
    if outcome.snapshot.divergence_type.strip():
        parts.append(outcome.snapshot.divergence_type.strip())
    return " · ".join(parts) if parts else "Gösterge bilgisi yok"


def _dimension_getters() -> tuple[
    tuple[str, Callable[[SignalOutcome], str]], ...
]:
    return (
        (
            "Piyasa rejimi",
            lambda item: item.snapshot.market_regime.strip()
            or "Rejim bilgisi yok",
        ),
        (
            "Sektör",
            lambda item: item.snapshot.sector.strip()
            or "Sektör bilgisi yok",
        ),
        (
            "Gösterge",
            _indicator_label,
        ),
        (
            "Günlük/haftalık yön",
            _direction_alignment,
        ),
        (
            "Hacim onayı",
            lambda item: _volume_label(
                item.snapshot.volume_confirmation
            ),
        ),
        (
            "Kalite bandı",
            lambda item: _quality_band(
                item.snapshot.quality_score
            ),
        ),
    )


def _build_row(
    *,
    dimension: str,
    group: str,
    horizon: int,
    items: list[tuple[SignalOutcome, object]],
    minimum_sample_size: int,
) -> ComparisonRow:
    returns = [
        float(result.close_return_percent)
        for _, result in items
        if result.close_return_percent is not None
    ]
    mfe_values = [
        float(result.maximum_favorable_excursion_percent)
        for _, result in items
        if result.maximum_favorable_excursion_percent is not None
    ]
    mae_values = [
        float(result.maximum_adverse_excursion_percent)
        for _, result in items
        if result.maximum_adverse_excursion_percent is not None
    ]
    target_1 = [
        bool(result.target_1_hit)
        for _, result in items
        if result.target_1_hit is not None
    ]
    target_2 = [
        bool(result.target_2_hit)
        for _, result in items
        if result.target_2_hit is not None
    ]
    stops = [
        bool(result.stop_hit)
        for _, result in items
        if result.stop_hit is not None
    ]
    successes = [value > 0 for value in returns]

    sample_count = len(returns)
    return ComparisonRow(
        dimension=dimension,
        group=group,
        horizon=horizon,
        sample_count=sample_count,
        success_count=sum(successes),
        success_rate_percent=round(_rate(successes) or 0.0, 2),
        average_return_percent=round(_average(returns), 4),
        median_return_percent=round(
            median(returns) if returns else 0.0,
            4,
        ),
        average_mfe_percent=round(_average(mfe_values), 4),
        average_mae_percent=round(_average(mae_values), 4),
        target_1_rate_percent=(
            None if not target_1 else round(_rate(target_1) or 0.0, 2)
        ),
        target_2_rate_percent=(
            None if not target_2 else round(_rate(target_2) or 0.0, 2)
        ),
        stop_rate_percent=(
            None if not stops else round(_rate(stops) or 0.0, 2)
        ),
        sample_status=(
            "Yeterli"
            if sample_count >= minimum_sample_size
            else f"Yetersiz örneklem (<{minimum_sample_size})"
        ),
    )


def build_success_comparison_report(
    outcomes: Iterable[SignalOutcome],
    *,
    minimum_sample_size: int = 5,
) -> SuccessComparisonReport:
    if minimum_sample_size < 1:
        raise SuccessComparisonError(
            "Minimum örneklem büyüklüğü en az 1 olmalıdır."
        )

    records = tuple(outcomes)
    rows: list[ComparisonRow] = []

    for dimension, getter in _dimension_getters():
        groups: dict[tuple[str, int], list[tuple[SignalOutcome, object]]] = {}
        for outcome in records:
            group = getter(outcome)
            for result in outcome.horizons:
                if not result.available:
                    continue
                groups.setdefault(
                    (group, result.horizon),
                    [],
                ).append((outcome, result))

        for (group, horizon), items in groups.items():
            rows.append(
                _build_row(
                    dimension=dimension,
                    group=group,
                    horizon=horizon,
                    items=items,
                    minimum_sample_size=minimum_sample_size,
                )
            )

    rows.sort(
        key=lambda item: (
            item.dimension,
            item.horizon,
            -item.sample_count,
            item.group,
        )
    )

    eligible = [
        item
        for item in rows
        if item.sample_count >= minimum_sample_size
    ]
    ranked = sorted(
        eligible,
        key=lambda item: (
            item.success_rate_percent,
            item.average_return_percent,
            item.sample_count,
        ),
        reverse=True,
    )

    return SuccessComparisonReport(
        rows=tuple(rows),
        minimum_sample_size=minimum_sample_size,
        strongest=tuple(ranked[:5]),
        weakest=tuple(reversed(ranked[-5:])),
    )


def comparison_rows(
    rows: Iterable[ComparisonRow],
) -> list[dict[str, object]]:
    return [
        {
            "Boyut": item.dimension,
            "Grup": item.group,
            "Ufuk": f"{item.horizon} gün",
            "Örneklem": item.sample_count,
            "Başarılı": item.success_count,
            "Başarı (%)": item.success_rate_percent,
            "Ort. getiri (%)": item.average_return_percent,
            "Medyan getiri (%)": item.median_return_percent,
            "Ort. MFE (%)": item.average_mfe_percent,
            "Ort. MAE (%)": item.average_mae_percent,
            "Hedef 1 (%)": item.target_1_rate_percent,
            "Hedef 2 (%)": item.target_2_rate_percent,
            "Stop (%)": item.stop_rate_percent,
            "Örneklem durumu": item.sample_status,
        }
        for item in rows
    ]


def comparison_csv_bytes(
    report: SuccessComparisonReport,
) -> bytes:
    rows = comparison_rows(report.rows)
    output = io.StringIO()
    fieldnames = list(rows[0]) if rows else [
        "Boyut",
        "Grup",
        "Ufuk",
        "Örneklem",
        "Başarı (%)",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def comparison_pdf_bytes(
    report: SuccessComparisonReport,
) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as error:
        raise SuccessComparisonError(
            "PDF üretimi için reportlab paketi gerekli."
        ) from error

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Rejim, Sektör ve Gösterge Başarı Karşılaştırması",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph(
            "Rejim, Sektör ve Gösterge Bazlı Başarı Karşılaştırması",
            styles["Title"],
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            (
                "Başarı, ilgili ölçüm ufkundaki kapanış getirisinin "
                "pozitif olması olarak tanımlanmıştır. Yetersiz örneklem "
                "grupları karar desteğinde tek başına kullanılmamalıdır."
            ),
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
    ]

    data = [[
        "Boyut", "Grup", "Ufuk", "N", "Başarı %",
        "Ort. Getiri", "MFE", "MAE", "Örneklem",
    ]]
    for item in report.rows:
        data.append([
            item.dimension,
            item.group,
            str(item.horizon),
            str(item.sample_count),
            f"{item.success_rate_percent:.1f}",
            f"{item.average_return_percent:.2f}",
            f"{item.average_mfe_percent:.2f}",
            f"{item.average_mae_percent:.2f}",
            item.sample_status,
        ])

    table = Table(
        data,
        repeatRows=1,
        colWidths=[
            30 * mm, 48 * mm, 14 * mm, 12 * mm, 20 * mm,
            22 * mm, 16 * mm, 16 * mm, 36 * mm,
        ],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(table)
    document.build(story)
    return buffer.getvalue()
