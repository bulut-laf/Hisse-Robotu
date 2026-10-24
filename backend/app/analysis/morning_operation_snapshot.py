from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .daily_operation_panel import DailyOperationSummary
from .morning_candidate_flow import (
    MorningCandidateCard,
    build_morning_candidate_cards,
)


@dataclass(frozen=True)
class MorningOperationSnapshot:
    operation_state: str
    operation_reason: str
    candidate_count: int
    candidates: tuple[MorningCandidateCard, ...]


def _critical_alert_count(summary: DailyOperationSummary) -> int:
    return sum(
        str(item.level).casefold() == "kritik"
        for item in summary.alerts
    )


def build_morning_operation_snapshot(
    *,
    operation_summary: DailyOperationSummary,
    scan_result: object,
    visibility_contexts: Iterable[object] = (),
    limit: int = 5,
) -> MorningOperationSnapshot:
    """
    Daily Operations sağlık kanıtı ile mevcut tarama adaylarını tek sabah
    snapshot'ında birleştirir.

    Yeni skor/sinyal üretmez. Veri güvenlik kilidi veya kritik operasyon
    uyarısı aday listesini kapatmaz; mevcut son güvenilir tarama sonucu
    uyarılı şekilde sunulmaya devam eder.
    """
    critical_count = _critical_alert_count(operation_summary)

    cards = build_morning_candidate_cards(
        scan_result,
        visibility_contexts=visibility_contexts,
        limit=limit,
        include_movement_pool=True,
    )

    warning_reasons: list[str] = []
    if operation_summary.delayed_data_locked:
        warning_reasons.append("Veri güvenlik kilidi aktif")
    if critical_count > 0:
        warning_reasons.append(f"{critical_count} kritik operasyon uyarısı mevcut")

    return MorningOperationSnapshot(
        operation_state="UYARILI_HAZIR" if warning_reasons else "HAZIR",
        operation_reason=(
            "; ".join(warning_reasons) + ". Son geçerli aday listesi korunuyor."
            if warning_reasons
            else "Sabah aday akışı operasyona hazır."
        ),
        candidate_count=len(cards),
        candidates=cards,
    )
