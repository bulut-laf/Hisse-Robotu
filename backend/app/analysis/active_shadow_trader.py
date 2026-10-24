from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ACTION_HOLD = "TUT"
ACTION_WATCH = "İZLE"
ACTION_EXIT_REVIEW = "ÇIKIŞI DEĞERLENDİR"
ACTION_STOP_EXIT = "STOP / ÇIKIŞ"

TECH_POSITIVE = "Pozitif"
TECH_NEUTRAL = "Nötr"
TECH_WEAK = "Bozuldu"
TECH_OPTIONS = (TECH_POSITIVE, TECH_NEUTRAL, TECH_WEAK)

NEWS_NONE = "Yok"
NEWS_WATCH = "İzle"
NEWS_HIGH = "Yüksek"
NEWS_OPTIONS = (NEWS_NONE, NEWS_WATCH, NEWS_HIGH)


class ActiveShadowTraderError(RuntimeError):
    """Aktif Gölge Portföy yönetim verisi hatası."""


@dataclass(frozen=True, slots=True)
class TraderPolicy:
    breakeven_r: float = 1.0
    profit_lock_r: float = 1.5
    trailing_r: float = 2.0
    profit_lock_offset_r: float = 0.25
    trailing_distance_r: float = 0.75
    max_holding_days: int = 5
    stale_progress_r: float = 0.50

    def __post_init__(self) -> None:
        numeric = (
            self.breakeven_r,
            self.profit_lock_r,
            self.trailing_r,
            self.profit_lock_offset_r,
            self.trailing_distance_r,
            self.stale_progress_r,
        )
        if any(not math.isfinite(item) or item < 0 for item in numeric):
            raise ValueError("Trader politika değerleri negatif veya geçersiz olamaz.")
        if not self.breakeven_r <= self.profit_lock_r <= self.trailing_r:
            raise ValueError("R eşikleri artan sırada olmalıdır.")
        if self.trailing_distance_r <= 0:
            raise ValueError("Trailing stop mesafesi sıfırdan büyük olmalıdır.")
        if not 1 <= int(self.max_holding_days) <= 60:
            raise ValueError("Maksimum elde tutma günü 1-60 aralığında olmalıdır.")


@dataclass(frozen=True, slots=True)
class TraderState:
    position_key: str
    active_stop: float | None = None
    high_water_price: float | None = None
    last_observed_price: float | None = None
    last_observed_at: str = ""
    observation_count: int = 0

    def __post_init__(self) -> None:
        if not str(self.position_key).strip():
            raise ValueError("position_key boş olamaz.")
        for name in ("active_stop", "high_water_price", "last_observed_price"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"{name} pozitif ve sonlu olmalıdır.")
        if self.observation_count < 0:
            raise ValueError("observation_count negatif olamaz.")


@dataclass(frozen=True, slots=True)
class TraderAssessment:
    position_key: str
    symbol: str
    manual_price: float
    entry_price: float
    initial_stop: float | None
    previous_active_stop: float | None
    recommended_stop: float | None
    high_water_price: float
    pnl_percent: float
    r_multiple: float | None
    holding_days: int
    action: str
    stop_phase: str
    stop_hit: bool
    time_review: bool
    technical_state: str
    news_risk: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TraderObservation:
    observed_at: str
    position_key: str
    symbol: str
    manual_price: float
    recommended_stop: float | None
    action: str
    technical_state: str
    news_risk: str
    reasons: tuple[str, ...]


def _normalize_symbol(symbol: object) -> str:
    value = str(symbol or "").strip().upper()
    if not value:
        raise ValueError("Pozisyon sembolü boş olamaz.")
    return value if "." in value else f"{value}.IS"


def _as_positive_float(value: object, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} sayısal olmalıdır.") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{label} pozitif ve sonlu olmalıdır.")
    return number


def _optional_positive_float(value: object) -> float | None:
    if value in (None, "", 0, 0.0):
        return None
    return _as_positive_float(value, "Fiyat")


def _position_entry_date(position: Any) -> date:
    raw = getattr(position, "entry_date", None)
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        try:
            return date.fromisoformat(raw[:10])
        except ValueError as exc:
            raise ValueError("Giriş tarihi ISO tarih formatında olmalıdır.") from exc
    raise ValueError("Pozisyonda geçerli giriş tarihi bulunamadı.")


def stable_position_key(position: Any) -> str:
    symbol = _normalize_symbol(getattr(position, "symbol", ""))
    entry_date = _position_entry_date(position).isoformat()
    entry_price = _as_positive_float(getattr(position, "entry_price", None), "Giriş fiyatı")
    quantity = int(getattr(position, "quantity", 0))
    if quantity <= 0:
        raise ValueError("Pozisyon lotu pozitif olmalıdır.")
    raw = f"{symbol}|{entry_date}|{entry_price:.8f}|{quantity}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{symbol.removesuffix('.IS')}-{entry_date}-{digest}"


def assess_shadow_position(
    position: Any,
    *,
    manual_price: float,
    state: TraderState | None = None,
    technical_state: str = TECH_NEUTRAL,
    news_risk: str = NEWS_NONE,
    observed_on: date | None = None,
    policy: TraderPolicy = TraderPolicy(),
) -> TraderAssessment:
    if technical_state not in TECH_OPTIONS:
        raise ValueError("Desteklenmeyen teknik görünüm.")
    if news_risk not in NEWS_OPTIONS:
        raise ValueError("Desteklenmeyen haber riski.")

    price = _as_positive_float(manual_price, "Manuel fiyat")
    entry = _as_positive_float(getattr(position, "entry_price", None), "Giriş fiyatı")
    initial_stop = _optional_positive_float(getattr(position, "stop_loss", None))
    key = stable_position_key(position)
    if state is not None and state.position_key != key:
        raise ValueError("Trader durumu farklı bir pozisyona ait.")

    previous_active_stop = None if state is None else state.active_stop
    prior_high = None if state is None else state.high_water_price
    high_water = max(price, prior_high or price)

    today = observed_on or date.today()
    entry_date = _position_entry_date(position)
    holding_days = max(0, (today - entry_date).days)

    pnl_percent = (price / entry - 1.0) * 100.0
    r_multiple: float | None = None
    recommended_stop = previous_active_stop or initial_stop
    stop_phase = "İlk stop"
    reasons: list[str] = []

    if initial_stop is not None and initial_stop < entry:
        initial_risk = entry - initial_stop
        r_multiple = (price - entry) / initial_risk
        max_r_multiple = (high_water - entry) / initial_risk
        candidates: list[tuple[float, str, str]] = [(initial_stop, "İlk stop", "İlk teknik stop korunuyor.")]
        if previous_active_stop is not None:
            candidates.append((previous_active_stop, "Mevcut aktif stop", "Daha önce yükseltilmiş stop aşağı indirilmez."))

        if max_r_multiple >= policy.breakeven_r or bool(getattr(position, "target_1_hit", False)):
            candidates.append((entry, "Başa baş", "Pozisyon en az 1R ilerledi; stop giriş fiyatına taşınabilir."))

        if max_r_multiple >= policy.profit_lock_r or bool(getattr(position, "target_1_hit", False)):
            candidates.append((
                entry + initial_risk * policy.profit_lock_offset_r,
                "Kâr koruma",
                "Pozisyon kâr koruma eşiğine ulaştı; başlangıç riskinin bir bölümü kilitlenebilir.",
            ))

        if max_r_multiple >= policy.trailing_r or bool(getattr(position, "target_2_hit", False)):
            candidates.append((
                high_water - initial_risk * policy.trailing_distance_r,
                "Trailing stop",
                "Güçlü ilerleme sonrası stop görülen en yüksek fiyatın arkasından izler.",
            ))

        valid_candidates = tuple(item for item in candidates if item[0] > 0)
        selected = max(valid_candidates, key=lambda item: item[0])
        recommended_stop, stop_phase, stop_reason = selected
        reasons.append(stop_reason)
    else:
        recommended_stop = previous_active_stop
        stop_phase = "Stop tanımsız"
        reasons.append("İlk stop tanımlı olmadığı için R bazlı stop yükseltmesi hesaplanmadı.")

    stop_hit = recommended_stop is not None and price <= recommended_stop
    time_review = (
        holding_days >= policy.max_holding_days
        and (r_multiple is None or r_multiple < policy.stale_progress_r)
    )

    if stop_hit:
        action = ACTION_STOP_EXIT
        reasons.append("Manuel fiyat aktif stop seviyesine geldi veya altına indi.")
    elif technical_state == TECH_WEAK or news_risk == NEWS_HIGH:
        action = ACTION_EXIT_REVIEW
        if technical_state == TECH_WEAK:
            reasons.append("Teknik görünüm manuel kontrolde bozuldu olarak işaretlendi.")
        if news_risk == NEWS_HIGH:
            reasons.append("Haber/olay riski yüksek olarak işaretlendi.")
    elif time_review:
        action = ACTION_EXIT_REVIEW
        reasons.append("Pozisyon zaman eşiğini aştı ve yeterli R ilerlemesi göstermedi.")
    elif technical_state == TECH_NEUTRAL or news_risk == NEWS_WATCH:
        action = ACTION_WATCH
        reasons.append("Yeni risk/teyit nedeniyle pozisyon yakın izlemeye alındı.")
    else:
        action = ACTION_HOLD
        reasons.append("Stop ihlali veya güçlü çıkış gerekçesi yok.")

    return TraderAssessment(
        position_key=key,
        symbol=_normalize_symbol(getattr(position, "symbol", "")),
        manual_price=price,
        entry_price=entry,
        initial_stop=initial_stop,
        previous_active_stop=previous_active_stop,
        recommended_stop=recommended_stop,
        high_water_price=high_water,
        pnl_percent=pnl_percent,
        r_multiple=r_multiple,
        holding_days=holding_days,
        action=action,
        stop_phase=stop_phase,
        stop_hit=stop_hit,
        time_review=time_review,
        technical_state=technical_state,
        news_risk=news_risk,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def next_state(
    assessment: TraderAssessment,
    previous: TraderState | None = None,
    *,
    observed_at: datetime | None = None,
    apply_recommended_stop: bool = False,
) -> TraderState:
    stamp = observed_at or datetime.now(timezone.utc)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("Gözlem zamanı saat dilimi içermelidir.")
    if previous is not None and previous.position_key != assessment.position_key:
        raise ValueError("Önceki durum farklı bir pozisyona ait.")

    active_stop = None if previous is None else previous.active_stop
    if apply_recommended_stop and assessment.recommended_stop is not None:
        active_stop = max(active_stop or 0.0, assessment.recommended_stop)

    high_water = assessment.high_water_price
    if previous is not None and previous.high_water_price is not None:
        high_water = max(high_water, previous.high_water_price)

    return TraderState(
        position_key=assessment.position_key,
        active_stop=active_stop,
        high_water_price=high_water,
        last_observed_price=assessment.manual_price,
        last_observed_at=stamp.isoformat(),
        observation_count=(0 if previous is None else previous.observation_count) + 1,
    )


class ActiveShadowTraderStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else Path.home() / ".hisse_robotu" / "active_shadow_trader"
        self.state_path = self.root / "state.json"
        self.observation_path = self.root / "observations.jsonl"
        self.root.mkdir(parents=True, exist_ok=True)

    def load(self, position_key: str) -> TraderState | None:
        if not self.state_path.exists():
            return None
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            raw = payload.get(position_key)
            return None if raw is None else TraderState(**raw)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ActiveShadowTraderError(f"Trader durum dosyası okunamadı: {exc}") from exc

    def save_state(self, state: TraderState) -> None:
        payload: dict[str, object] = {}
        if self.state_path.exists():
            try:
                loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    payload = loaded
            except (OSError, json.JSONDecodeError) as exc:
                raise ActiveShadowTraderError(f"Trader durum dosyası okunamadı: {exc}") from exc
        payload[state.position_key] = asdict(state)
        temp = self.state_path.with_suffix(".tmp")
        try:
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(self.state_path)
        except OSError as exc:
            raise ActiveShadowTraderError(f"Trader durumu kaydedilemedi: {exc}") from exc

    def append_observation(self, assessment: TraderAssessment, *, observed_at: datetime | None = None) -> None:
        stamp = observed_at or datetime.now(timezone.utc)
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError("Gözlem zamanı saat dilimi içermelidir.")
        item = TraderObservation(
            observed_at=stamp.isoformat(),
            position_key=assessment.position_key,
            symbol=assessment.symbol,
            manual_price=assessment.manual_price,
            recommended_stop=assessment.recommended_stop,
            action=assessment.action,
            technical_state=assessment.technical_state,
            news_risk=assessment.news_risk,
            reasons=assessment.reasons,
        )
        try:
            with self.observation_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
        except OSError as exc:
            raise ActiveShadowTraderError(f"Trader gözlemi kaydedilemedi: {exc}") from exc

    def record_assessment(
        self,
        assessment: TraderAssessment,
        *,
        previous: TraderState | None,
        apply_recommended_stop: bool,
        observed_at: datetime | None = None,
    ) -> TraderState:
        stamp = observed_at or datetime.now(timezone.utc)
        state = next_state(
            assessment,
            previous,
            observed_at=stamp,
            apply_recommended_stop=apply_recommended_stop,
        )
        self.save_state(state)
        self.append_observation(assessment, observed_at=stamp)
        return state


def assessment_rows(items: tuple[TraderAssessment, ...]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in items:
        rows.append({
            "Hisse": item.symbol.removesuffix(".IS"),
            "Fiyat": round(item.manual_price, 4),
            "Getiri (%)": round(item.pnl_percent, 2),
            "R": None if item.r_multiple is None else round(item.r_multiple, 2),
            "Aktif stop": None if item.recommended_stop is None else round(item.recommended_stop, 4),
            "Stop fazı": item.stop_phase,
            "Elde tutma (gün)": item.holding_days,
            "Teknik": item.technical_state,
            "Haber riski": item.news_risk,
            "Trader kararı": item.action,
            "Gerekçe": " | ".join(item.reasons),
        })
    return rows
