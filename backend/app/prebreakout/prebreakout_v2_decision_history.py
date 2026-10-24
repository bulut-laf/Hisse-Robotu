from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
import json
from pathlib import Path

from backend.app.prebreakout.prebreakout_v2_decision_stability import (
    DecisionSnapshot,
    DecisionStabilityReport,
)
from backend.app.prebreakout.prebreakout_v2_first_live_evaluation import ModelDecision


class PeriodComparison(str, Enum):
    YETERSIZ_VERI = "Yetersiz veri"
    IYILESIYOR = "İyileşiyor"
    BENZER = "Benzer"
    KOTULESIYOR = "Kötüleşiyor"


@dataclass(frozen=True)
class DecisionHistoryRecord:
    period_id: str
    recorded_on: str
    observation_day: int
    decision: str
    success_rate_pct: float | None
    false_positive_rate_pct: float | None
    portfolio_return_pct: float | None


@dataclass(frozen=True)
class PeriodSummary:
    period_id: str
    record_count: int
    dominant_decision: str | None
    model_keep_share: float
    calibration_share: float
    avg_success_rate_pct: float | None
    avg_false_positive_rate_pct: float | None
    avg_portfolio_return_pct: float | None


@dataclass(frozen=True)
class PeriodComparisonReport:
    current_period: str
    previous_period: str | None
    comparison: PeriodComparison
    reasons: tuple[str, ...]
    current_summary: PeriodSummary
    previous_summary: PeriodSummary | None
    summary: str


def karar_gecmisi_kaydi_olustur(
    snapshot: DecisionSnapshot,
    *,
    period_id: str,
    recorded_on: str | None = None,
) -> DecisionHistoryRecord:
    return DecisionHistoryRecord(
        period_id=period_id.strip(),
        recorded_on=recorded_on or date.today().isoformat(),
        observation_day=snapshot.observation_day,
        decision=snapshot.decision.value,
        success_rate_pct=snapshot.success_rate_pct,
        false_positive_rate_pct=snapshot.false_positive_rate_pct,
        portfolio_return_pct=snapshot.portfolio_return_pct,
    )


def karar_gecmisini_yukle(path: str | Path) -> tuple[DecisionHistoryRecord, ...]:
    p = Path(path)
    if not p.exists():
        return ()
    records: list[DecisionHistoryRecord] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(DecisionHistoryRecord(**json.loads(line)))
    return tuple(records)


def karar_gecmisine_ekle(
    path: str | Path,
    record: DecisionHistoryRecord,
) -> bool:
    """Append-only karar geçmişi.

    Aynı period_id + observation_day kaydı tekrar yazılmaz.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = karar_gecmisini_yukle(p)
    key = (record.period_id, record.observation_day)
    if any((x.period_id, x.observation_day) == key for x in existing):
        return False
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return True


def _avg(values):
    vals = [float(v) for v in values if v is not None]
    return None if not vals else round(sum(vals) / len(vals), 4)


def donemi_ozetle(
    records: tuple[DecisionHistoryRecord, ...] | list[DecisionHistoryRecord],
    period_id: str,
) -> PeriodSummary:
    selected = [x for x in records if x.period_id == period_id]
    if not selected:
        return PeriodSummary(period_id, 0, None, 0.0, 0.0, None, None, None)

    counts: dict[str, int] = {}
    for item in selected:
        counts[item.decision] = counts.get(item.decision, 0) + 1
    dominant = max(counts, key=counts.get)
    n = len(selected)
    keep = counts.get(ModelDecision.MODELI_KORU.value, 0) / n
    calibration = counts.get(ModelDecision.KALIBRASYON_ADAYI.value, 0) / n

    return PeriodSummary(
        period_id=period_id,
        record_count=n,
        dominant_decision=dominant,
        model_keep_share=round(keep, 4),
        calibration_share=round(calibration, 4),
        avg_success_rate_pct=_avg(x.success_rate_pct for x in selected),
        avg_false_positive_rate_pct=_avg(x.false_positive_rate_pct for x in selected),
        avg_portfolio_return_pct=_avg(x.portfolio_return_pct for x in selected),
    )


def kullanim_donemlerini_karsilastir(
    records: tuple[DecisionHistoryRecord, ...] | list[DecisionHistoryRecord],
    *,
    current_period: str,
    previous_period: str | None,
    minimum_records_per_period: int = 3,
) -> PeriodComparisonReport:
    current = donemi_ozetle(records, current_period)
    previous = donemi_ozetle(records, previous_period) if previous_period else None

    if (
        previous is None
        or current.record_count < minimum_records_per_period
        or previous.record_count < minimum_records_per_period
    ):
        return PeriodComparisonReport(
            current_period=current_period,
            previous_period=previous_period,
            comparison=PeriodComparison.YETERSIZ_VERI,
            reasons=(f"Her dönem için en az {minimum_records_per_period} karar kaydı gerekli.",),
            current_summary=current,
            previous_summary=previous,
            summary="Dönemler arası model kararı üretmek için geçmiş veri birikimi sürdürülmeli.",
        )

    score = 0
    reasons: list[str] = []

    if current.model_keep_share > previous.model_keep_share + 0.15:
        score += 1
        reasons.append("Modeli koru karar payı belirgin arttı.")
    elif current.model_keep_share + 0.15 < previous.model_keep_share:
        score -= 1
        reasons.append("Modeli koru karar payı belirgin azaldı.")

    if current.calibration_share + 0.15 < previous.calibration_share:
        score += 1
        reasons.append("Kalibrasyon adayı karar payı azaldı.")
    elif current.calibration_share > previous.calibration_share + 0.15:
        score -= 1
        reasons.append("Kalibrasyon adayı karar payı arttı.")

    if current.avg_success_rate_pct is not None and previous.avg_success_rate_pct is not None:
        delta = current.avg_success_rate_pct - previous.avg_success_rate_pct
        if delta >= 5:
            score += 1
            reasons.append("Ortalama başarı oranı en az 5 puan arttı.")
        elif delta <= -5:
            score -= 1
            reasons.append("Ortalama başarı oranı en az 5 puan düştü.")

    if (
        current.avg_false_positive_rate_pct is not None
        and previous.avg_false_positive_rate_pct is not None
    ):
        delta = current.avg_false_positive_rate_pct - previous.avg_false_positive_rate_pct
        if delta <= -5:
            score += 1
            reasons.append("Yanlış pozitif oranı en az 5 puan azaldı.")
        elif delta >= 5:
            score -= 1
            reasons.append("Yanlış pozitif oranı en az 5 puan arttı.")

    if (
        current.avg_portfolio_return_pct is not None
        and previous.avg_portfolio_return_pct is not None
    ):
        delta = current.avg_portfolio_return_pct - previous.avg_portfolio_return_pct
        if delta >= 2:
            score += 1
            reasons.append("Deneme portföyü getirisi en az 2 puan arttı.")
        elif delta <= -2:
            score -= 1
            reasons.append("Deneme portföyü getirisi en az 2 puan düştü.")

    if score >= 2:
        comparison = PeriodComparison.IYILESIYOR
        summary = "Gerçek kullanım dönemi önceki döneme göre iyileşiyor."
    elif score <= -2:
        comparison = PeriodComparison.KOTULESIYOR
        summary = "Gerçek kullanım dönemi önceki döneme göre kötüleşiyor; neden analizi gerekli."
    else:
        comparison = PeriodComparison.BENZER
        if not reasons:
            reasons.append("Dönemler arasında anlamlı eşik aşan fark yok.")
        summary = "Gerçek kullanım dönemleri benzer; mevcut model kararı korunmalı."

    return PeriodComparisonReport(
        current_period=current_period,
        previous_period=previous_period,
        comparison=comparison,
        reasons=tuple(reasons),
        current_summary=current,
        previous_summary=previous,
        summary=summary,
    )


def donem_karsilastirma_raporunu_metne_cevir(report: PeriodComparisonReport) -> str:
    prev = report.previous_summary
    return "\n".join(
        [
            "V2 GERÇEK KULLANIM - DÖNEM KARŞILAŞTIRMASI",
            f"Güncel dönem: {report.current_period}",
            f"Önceki dönem: {report.previous_period or 'Yok'}",
            f"Sonuç: {report.comparison.value}",
            f"Güncel kayıt sayısı: {report.current_summary.record_count}",
            f"Önceki kayıt sayısı: {prev.record_count if prev else 0}",
            f"Güncel baskın karar: {report.current_summary.dominant_decision or 'Yok'}",
            f"Önceki baskın karar: {prev.dominant_decision if prev else 'Yok'}",
            "Nedenler:",
            *[f"- {x}" for x in report.reasons],
            f"Özet: {report.summary}",
        ]
    )
