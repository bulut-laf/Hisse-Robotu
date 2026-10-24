from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.app.analysis.jump_candidate_quality import (
    evaluate_jump_candidate_quality,
)
from backend.app.analysis.jump_candidate_entry_readiness import (
    evaluate_jump_candidate_entry_readiness,
)
from backend.app.analysis.jump_candidate_priority_merge import (
    merge_jump_and_scan_candidates,
)


@dataclass(frozen=True)
class MorningCandidateCard:
    rank: int
    symbol: str
    technical_score: int
    technical_view: str
    research_priority: str
    visibility_state: str | None
    rank_change: int | None
    data_blocked: bool
    volume_ratio: float
    risk_reward: float
    reference_price: float | None
    positive_reasons: tuple[str, ...]
    risks: tuple[str, ...]
    operational_status: str
    selection_source: str = "TARAMA"
    selection_reason: str = ""
    jump_quality: str = "-"
    jump_quality_reason: str = ""
    entry_readiness: str = "-"
    entry_readiness_reason: str = ""
    entry_extension_atr: float | None = None
    priority_reason: str = ""


def _normalize_symbol(value: object) -> str:
    return str(value or "").strip().upper().removesuffix(".IS")


def _visibility_by_symbol(
    contexts: Iterable[object],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for context in contexts:
        symbol = _normalize_symbol(getattr(context, "symbol", ""))
        if symbol:
            result[symbol] = context
    return result



def _reference_price(candidate: object) -> float | None:
    for name in ("son_fiyat", "son_kapanis", "kapanis", "fiyat", "close"):
        value = getattr(candidate, name, None)
        if value in (None, ""):
            continue
        try:
            price = float(value)
        except (TypeError, ValueError):
            continue
        if price > 0:
            return price
    return None


def _operational_status(
    *,
    technical_view: str,
    research_priority: str,
    data_blocked: bool,
) -> str:
    if data_blocked:
        return "KISMİ VERİ — İNCELEMEYE DEVAM"

    if research_priority == "HIGH":
        return "ARAŞTIRMA ÖNCELİĞİ YÜKSEK"

    if technical_view == "Pozitif Teknik Görünüm":
        return "TEKNİK ADAY"

    return "TEYİT BEKLİYOR"




def _selection_reason(*, source: str, rank_change: int | None) -> str:
    if source == "SICRAMA":
        if rank_change is not None:
            return f"Pozitif sıra hareketi (+{rank_change}) nedeniyle sıçrama havuzundan seçildi."
        return "Pozitif sıra hareketi nedeniyle sıçrama havuzundan seçildi."
    return "Mevcut BIST Toplu Tarama sırasından seçildi."


def _candidate_selection(
    candidates: tuple[object, ...],
    visibility: dict[str, object],
    *,
    limit: int,
) -> tuple[tuple[object, str, str], ...]:
    merged = merge_jump_and_scan_candidates(
        candidates,
        visibility,
        limit=limit,
    )
    return tuple(
        (item.candidate, item.source, item.priority_reason)
        for item in merged
    )

def build_morning_candidate_cards(
    scan_result: object,
    *,
    visibility_contexts: Iterable[object] = (),
    limit: int = 5,
    include_movement_pool: bool = False,
) -> tuple[MorningCandidateCard, ...]:
    """
    Mevcut BIST toplu tarama sırasını değiştirmeden ilk sabah aday kartlarını
    üretir.

    Bu adapter yeni skor/sinyal üretmez. BatchStockScanner/MarketScanResult
    tarafından belirlenmiş aday sırasını korur; Early Visibility yalnız
    araştırma bağlamı ve veri-blok durumu olarak karta eklenir.
    """
    if limit < 1:
        raise ValueError("limit en az 1 olmalıdır.")

    candidates = tuple(getattr(scan_result, "adaylar", ()))
    visibility = _visibility_by_symbol(visibility_contexts)

    cards: list[MorningCandidateCard] = []

    selected = (
        _candidate_selection(candidates, visibility, limit=limit)
        if include_movement_pool
        else tuple((candidate, "TARAMA", "Mevcut tarama sırası korunuyor.") for candidate in candidates[:limit])
    )

    for rank, (candidate, selection_source, priority_reason) in enumerate(selected, start=1):
        symbol = _normalize_symbol(getattr(candidate, "sembol", ""))
        signal = getattr(candidate, "sinyal")
        risk_plan = getattr(candidate, "risk_plani")
        context = visibility.get(symbol)

        research_priority = (
            str(getattr(context, "research_priority", "NORMAL")).upper()
            if context is not None
            else "NORMAL"
        )
        data_blocked = bool(
            getattr(context, "data_blocked", False)
            if context is not None
            else False
        )
        visibility_state = (
            str(getattr(context, "visibility_state"))
            if context is not None
            and getattr(context, "visibility_state", None) is not None
            else None
        )
        rank_change = (
            int(getattr(context, "rank_change"))
            if context is not None
            and getattr(context, "rank_change", None) is not None
            else None
        )

        technical_view = str(getattr(signal, "karar"))

        _jump_quality = evaluate_jump_candidate_quality(candidate)
        _entry_readiness = evaluate_jump_candidate_entry_readiness(candidate)

        cards.append(
            MorningCandidateCard(
                rank=rank,
                symbol=symbol,
                technical_score=int(getattr(signal, "skor")),
                technical_view=technical_view,
                research_priority=research_priority,
                visibility_state=visibility_state,
                rank_change=rank_change,
                data_blocked=data_blocked,
                volume_ratio=float(getattr(candidate, "hacim_orani")),
                risk_reward=float(getattr(risk_plan, "risk_odul_orani")),
                reference_price=_reference_price(candidate),
                positive_reasons=tuple(
                    getattr(signal, "pozitif_nedenler", ())
                ),
                risks=tuple(getattr(signal, "riskler", ())),
                operational_status=_operational_status(
                    technical_view=technical_view,
                    research_priority=research_priority,
                    data_blocked=data_blocked,
                ),
                selection_source=selection_source,
                selection_reason=_selection_reason(
                    source=selection_source,
                    rank_change=rank_change,
                ),
                jump_quality=(
                    "UYGUN" if _jump_quality.eligible else "FİLTRE DIŞI"
                ),
                jump_quality_reason=" · ".join(_jump_quality.reasons),
                entry_readiness=_entry_readiness.state,
                entry_readiness_reason=" · ".join(_entry_readiness.reasons),
                entry_extension_atr=_entry_readiness.extension_atr,
                priority_reason=priority_reason,
            )
        )

    return tuple(cards)


def morning_candidate_rows(
    cards: Iterable[MorningCandidateCard],
) -> tuple[dict[str, object], ...]:
    """UI/tablo katmanı için sade, salt-okunur sabah aday satırları üretir."""
    return tuple(
        {
            "Sıra": card.rank,
            "Hisse": card.symbol,
            "Aday kaynağı": card.selection_source,
            "Seçim nedeni": card.selection_reason,
            "Top-5 öncelik nedeni": card.priority_reason,
            "Sıçrama kalite kapısı": card.jump_quality,
            "Sıçrama kalite nedeni": card.jump_quality_reason,
            "Giriş hazırlığı": card.entry_readiness,
            "Giriş hazırlığı nedeni": card.entry_readiness_reason,
            "Uzama (ATR)": (
                round(card.entry_extension_atr, 2)
                if card.entry_extension_atr is not None
                else "-"
            ),
            "Skor": card.technical_score,
            "Teknik görünüm": card.technical_view,
            "Araştırma önceliği": card.research_priority,
            "Erken görünürlük": card.visibility_state or "-",
            "Sıra değişimi": card.rank_change if card.rank_change is not None else "-",
            "Hacim oranı": round(card.volume_ratio, 2),
            "Risk/Getiri": round(card.risk_reward, 2),
            "Referans fiyat": round(card.reference_price, 4) if card.reference_price is not None else "-",
            "Durum": card.operational_status,
            "Nedenler": " | ".join(card.positive_reasons) or "-",
            "Riskler": " | ".join(card.risks) or "-",
        }
        for card in cards
    )
