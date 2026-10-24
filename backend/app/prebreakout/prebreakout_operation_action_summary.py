from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Iterable

from backend.app.prebreakout.prebreakout_operation_confidence import (
    DailyOperationDecision,
    OperationConfidenceReport,
)
from backend.app.prebreakout.prebreakout_operation_diagnosis import RootCauseCategory
from backend.app.prebreakout.prebreakout_operation_recovery import (
    OperationRecoveryGuide,
    RecoveryStep,
)


DEFAULT_OPERATION_ACTION_SUMMARY_PATH = Path(
    "backend/data/prebreakout_operation_action_summary.json"
)


class UserActionPriority(str, Enum):
    NORMAL = "NORMAL"
    ATTENTION = "DIKKAT"
    STOP = "DUR"


@dataclass(frozen=True)
class OperationActionSummary:
    run_date: str
    decision: DailyOperationDecision
    score: int
    priority: UserActionPriority
    headline: str
    why: tuple[str, ...]
    actions: tuple[str, ...]
    retry_allowed: bool
    final_message: str


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _priority(report: OperationConfidenceReport) -> UserActionPriority:
    if report.decision is DailyOperationDecision.WAIT:
        return UserActionPriority.STOP
    if report.decision is DailyOperationDecision.REVIEW:
        return UserActionPriority.ATTENTION
    return UserActionPriority.NORMAL


def _headline(report: OperationConfidenceReport) -> str:
    if report.decision is DailyOperationDecision.RUN:
        return "Günlük operasyon kullanılabilir durumda."
    if report.decision is DailyOperationDecision.WAIT:
        return "Günlük operasyonu durdur; kritik nedeni önce gider."
    return "Günlük operasyon sonucunu incelemeden devam etme."


def _plain_reason(category: RootCauseCategory) -> str | None:
    mapping = {
        RootCauseCategory.DATA: "Piyasa verisi güvenilir veya yeterince güncel değil.",
        RootCauseCategory.RECORD_INTEGRITY: "Operasyon kayıt zincirinde tutarsızlık bulundu.",
        RootCauseCategory.HEALTH_LOCK: "Sistem sağlık kontrolü operasyonu güvenlik nedeniyle durdurdu.",
        RootCauseCategory.CALCULATION: "Bir hesaplama adımı doğrulama gerektiriyor.",
        RootCauseCategory.PORTFOLIO: "Deneme portföyü kayıtları doğrulama gerektiriyor.",
        RootCauseCategory.OPERATION: "Günlük operasyon akışında teknik bir hata oluştu.",
        RootCauseCategory.NONE: None,
    }
    return mapping[category]


def _step_text(step: RecoveryStep) -> str:
    title = str(step.title).strip()
    instruction = str(step.instruction).strip()
    if title and instruction and instruction.lower() not in title.lower():
        return f"{title}: {instruction}"
    return instruction or title


def operasyon_aksiyon_ozeti_olustur(
    confidence: OperationConfidenceReport,
    recovery: OperationRecoveryGuide,
    *,
    max_reasons: int = 3,
    max_actions: int = 3,
) -> OperationActionSummary:
    """Teknik güven/teşhis çıktısını kısa kullanıcı aksiyonuna dönüştürür.

    Bu katman herhangi bir düzeltme veya yeniden deneme başlatmaz. Yalnızca
    mevcut kararın nedenini ve güvenli sonraki adımı sadeleştirir.
    """
    reasons: list[str] = []
    plain = _plain_reason(confidence.primary_category)
    if plain:
        reasons.append(plain)
    if confidence.error_count:
        reasons.append(f"Sistem sağlık raporunda {confidence.error_count} hata var.")
    if confidence.warning_count:
        reasons.append(f"Sistem sağlık raporunda {confidence.warning_count} uyarı var.")
    reasons.extend(confidence.reasons)
    why = _unique(reasons)[: max(1, int(max_reasons))]

    actions = _unique(_step_text(step) for step in recovery.steps)
    if confidence.decision is DailyOperationDecision.RUN:
        actions = ("Günlük operasyon akışına normal şekilde devam et.",)
    elif not actions:
        actions = ("Teknik ayrıntıları incele ve kök neden doğrulanmadan işlem yapma.",)
    actions = actions[: max(1, int(max_actions))]

    retry_allowed = bool(recovery.safe_retry_allowed)
    if confidence.decision is DailyOperationDecision.WAIT:
        retry_allowed = False

    if confidence.decision is DailyOperationDecision.RUN:
        final_message = (
            f"ÇALIŞTIR — güven skoru {confidence.score}/100. "
            "Mevcut kontroller günlük kullanıma izin veriyor."
        )
    elif confidence.decision is DailyOperationDecision.WAIT:
        final_message = (
            f"BEKLE — güven skoru {confidence.score}/100. "
            "Kritik neden çözülmeden operasyonu yeniden çalıştırma."
        )
    elif retry_allowed:
        final_message = (
            f"İNCELE — güven skoru {confidence.score}/100. "
            "Önerilen doğrulama tamamlandıktan sonra kontrollü yeniden deneme yapılabilir."
        )
    else:
        final_message = (
            f"İNCELE — güven skoru {confidence.score}/100. "
            "Manuel doğrulama tamamlanmadan yeniden deneme yapma."
        )

    return OperationActionSummary(
        run_date=confidence.run_date,
        decision=confidence.decision,
        score=confidence.score,
        priority=_priority(confidence),
        headline=_headline(confidence),
        why=why,
        actions=actions,
        retry_allowed=retry_allowed,
        final_message=final_message,
    )


def operasyon_aksiyon_ozetini_kaydet(
    summary: OperationActionSummary,
    path: str | Path = DEFAULT_OPERATION_ACTION_SUMMARY_PATH,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(summary)
    payload["decision"] = summary.decision.value
    payload["priority"] = summary.priority.value
    payload["why"] = list(summary.why)
    payload["actions"] = list(summary.actions)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def operasyon_aksiyon_ozetini_tabloya_cevir(
    summary: OperationActionSummary,
) -> list[dict[str, str]]:
    rows = [
        {"Alan": "Karar", "Değer": summary.decision.value},
        {"Alan": "Güven skoru", "Değer": f"{summary.score}/100"},
        {"Alan": "Öncelik", "Değer": summary.priority.value},
        {"Alan": "Yeniden deneme", "Değer": "Uygun" if summary.retry_allowed else "Bekle"},
    ]
    rows.extend(
        {"Alan": f"Neden {index}", "Değer": value}
        for index, value in enumerate(summary.why, start=1)
    )
    rows.extend(
        {"Alan": f"Aksiyon {index}", "Değer": value}
        for index, value in enumerate(summary.actions, start=1)
    )
    return rows
