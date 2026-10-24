from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
import unicodedata


class StreamlitLike(Protocol):
    def subheader(self, body: str) -> Any: ...
    def caption(self, body: str) -> Any: ...
    def metric(self, label: str, value: Any, delta: Any | None = None) -> Any: ...
    def info(self, body: str) -> Any: ...
    def warning(self, body: str) -> Any: ...
    def success(self, body: str) -> Any: ...
    def markdown(self, body: str) -> Any: ...


@dataclass(frozen=True)
class EarlyRadarCard:
    symbol: str
    early_radar: str
    opportunity_score: float
    movement_phase: str
    maturity: str
    new_entry_message: str
    position_message: str
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol boş olamaz.")
        if not 0 <= self.opportunity_score <= 100:
            raise ValueError("opportunity_score 0-100 arasında olmalıdır.")


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def card_from_output(symbol: str, output: Any) -> EarlyRadarCard:
    return EarlyRadarCard(
        symbol=symbol.upper(),
        early_radar=str(getattr(output.early_radar, "value", output.early_radar)),
        opportunity_score=float(output.priority_score),
        movement_phase=str(output.movement_phase),
        maturity=str(getattr(output.maturity, "value", output.maturity)),
        new_entry_message=str(output.new_entry_message),
        position_message=str(output.position_message),
        reasons=tuple(str(x) for x in output.reasons),
    )


def status_level(card: EarlyRadarCard) -> str:
    maturity = _norm(card.maturity)
    radar = _norm(card.early_radar)

    if "kar koruma" in maturity:
        return "warning"
    if "yuksek" in radar:
        return "success"
    if "izle" in radar or "olgunlasiyor" in maturity:
        return "info"
    return "neutral"


def compact_summary(card: EarlyRadarCard) -> str:
    return (
        f"{card.symbol} · Erken Radar: {card.early_radar} · "
        f"Fırsat: {card.opportunity_score:.0f}/100 · "
        f"Faz: {card.movement_phase} · Olgunlaşma: {card.maturity}"
    )


def as_row(card: EarlyRadarCard) -> dict[str, object]:
    return {
        "Hisse": card.symbol,
        "Erken Radar": card.early_radar,
        "Erken Fırsat": round(card.opportunity_score, 1),
        "Hareket Fazı": card.movement_phase,
        "Olgunlaşma": card.maturity,
        "Yeni Giriş": card.new_entry_message,
        "Mevcut Pozisyon": card.position_message,
    }


def sort_cards(cards: list[EarlyRadarCard]) -> list[EarlyRadarCard]:
    def key(card: EarlyRadarCard) -> tuple[int, float, str]:
        warning = 1 if status_level(card) == "warning" else 0
        return (warning, -card.opportunity_score, card.symbol)

    return sorted(cards, key=key)


def split_cards(
    cards: list[EarlyRadarCard],
) -> tuple[list[EarlyRadarCard], list[EarlyRadarCard]]:
    early: list[EarlyRadarCard] = []
    maturity: list[EarlyRadarCard] = []

    for card in sort_cards(cards):
        if status_level(card) == "warning":
            maturity.append(card)
        elif _norm(card.early_radar) != "yok":
            early.append(card)

    return early, maturity


def render_early_radar_card(st: StreamlitLike, card: EarlyRadarCard) -> None:
    st.subheader(card.symbol)
    st.caption(
        f"Erken Radar: {card.early_radar} · "
        f"Hareket Fazı: {card.movement_phase} · "
        f"Olgunlaşma: {card.maturity}"
    )
    st.metric("Erken Fırsat Puanı", f"{card.opportunity_score:.0f}/100")

    level = status_level(card)
    if level == "warning":
        st.warning(card.new_entry_message)
        st.warning(card.position_message)
    elif level == "success":
        st.success(card.new_entry_message)
        st.info(card.position_message)
    elif level == "info":
        st.info(card.new_entry_message)
        st.info(card.position_message)
    else:
        st.caption(card.new_entry_message)
        st.caption(card.position_message)

    if card.reasons:
        st.markdown("**Gerekçeler**")
        for reason in card.reasons:
            st.markdown(f"- {reason}")


def render_early_radar_panel(
    st: StreamlitLike,
    cards: list[EarlyRadarCard],
) -> None:
    early, maturity = split_cards(cards)

    st.subheader("Erken Radar")
    st.caption(
        "Ana teknik skordan bağımsız erken fırsat görünümüdür; "
        "mevcut aday sıralamasını değiştirmez."
    )

    if not early:
        st.info("Şu anda Erken Radar adayı yok.")
    else:
        for card in early:
            render_early_radar_card(st, card)

    st.subheader("Olgunlaşma / Kâr Koruma")
    st.caption(
        "İlk sıralara ulaşmış ve hareket yaşı/getirisi yükselmiş adaylar "
        "ayrı gösterilir."
    )

    if not maturity:
        st.info("Şu anda Kâr Koruma uyarısı yok.")
    else:
        for card in maturity:
            render_early_radar_card(st, card)
