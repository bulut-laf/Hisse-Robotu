from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.app.prebreakout.prebreakout_v2_decision_history import (
    PeriodComparison,
    PeriodComparisonReport,
)


class DeteriorationSignal(str, Enum):
    YOK = "Yok"
    IZLE = "İzle"
    KALICI_BOZULMA = "Kalıcı bozulma"


@dataclass(frozen=True)
class CalibrationGatePolicy:
    minimum_comparisons: int = 3
    minimum_worsening_count: int = 2
    require_latest_worsening: bool = True


@dataclass(frozen=True)
class CalibrationGateReport:
    comparison_count: int
    worsening_count: int
    latest_comparison: PeriodComparison | None
    signal: DeteriorationSignal
    calibration_review_open: bool
    reasons: tuple[str, ...]
    summary: str


def kalibrasyon_inceleme_kapisini_degerlendir(
    comparisons: tuple[PeriodComparisonReport, ...] | list[PeriodComparisonReport],
    *,
    policy: CalibrationGatePolicy | None = None,
) -> CalibrationGateReport:
    policy = policy or CalibrationGatePolicy()
    items = list(comparisons)
    n = len(items)

    if n == 0:
        return CalibrationGateReport(
            comparison_count=0,
            worsening_count=0,
            latest_comparison=None,
            signal=DeteriorationSignal.YOK,
            calibration_review_open=False,
            reasons=("Henüz dönem karşılaştırması yok.",),
            summary="Kalibrasyon incelemesi açılmaz; gerçek kullanım verisi birikmeye devam etmeli.",
        )

    latest = items[-1].comparison
    worsening_count = sum(1 for x in items if x.comparison is PeriodComparison.KOTULESIYOR)

    if n < policy.minimum_comparisons:
        return CalibrationGateReport(
            comparison_count=n,
            worsening_count=worsening_count,
            latest_comparison=latest,
            signal=DeteriorationSignal.IZLE,
            calibration_review_open=False,
            reasons=(f"En az {policy.minimum_comparisons} dönem karşılaştırması gerekli.",),
            summary="Henüz kalıcı bozulma kararı vermek için dönem geçmişi yeterli değil.",
        )

    latest_ok = (
        latest is PeriodComparison.KOTULESIYOR
        if policy.require_latest_worsening
        else True
    )

    persistent = (
        worsening_count >= policy.minimum_worsening_count
        and latest_ok
    )

    if persistent:
        reasons = (
            f"{n} karşılaştırmanın {worsening_count} tanesi kötüleşiyor.",
            "Son dönem de kötüleşme yönünde." if latest is PeriodComparison.KOTULESIYOR else "Son dönem koşulu aranmadı.",
        )
        return CalibrationGateReport(
            comparison_count=n,
            worsening_count=worsening_count,
            latest_comparison=latest,
            signal=DeteriorationSignal.KALICI_BOZULMA,
            calibration_review_open=True,
            reasons=reasons,
            summary=(
                "Bozulma tek döneme özgü görünmüyor. Kontrollü kalibrasyon incelemesi açılabilir; "
                "üretim eşikleri otomatik değiştirilmez."
            ),
        )

    return CalibrationGateReport(
        comparison_count=n,
        worsening_count=worsening_count,
        latest_comparison=latest,
        signal=DeteriorationSignal.YOK if worsening_count == 0 else DeteriorationSignal.IZLE,
        calibration_review_open=False,
        reasons=(
            "Bozulma sinyali kalıcı eşiklerini karşılamıyor.",
        ),
        summary=(
            "Model değişikliği için yeterli kalıcı bozulma kanıtı yok. "
            "Mevcut V2 modeli korunarak gözleme devam edilmeli."
        ),
    )


def kalibrasyon_kapisi_raporunu_metne_cevir(report: CalibrationGateReport) -> str:
    latest = report.latest_comparison.value if report.latest_comparison else "Yok"
    return "\n".join(
        [
            "V2 GERÇEK KULLANIM - KALİBRASYON İNCELEME KAPISI",
            f"Dönem karşılaştırması: {report.comparison_count}",
            f"Kötüleşen dönem sayısı: {report.worsening_count}",
            f"Son dönem sonucu: {latest}",
            f"Sinyal: {report.signal.value}",
            f"Kalibrasyon incelemesi açık: {'EVET' if report.calibration_review_open else 'HAYIR'}",
            "Nedenler:",
            *[f"- {x}" for x in report.reasons],
            f"Özet: {report.summary}",
        ]
    )
