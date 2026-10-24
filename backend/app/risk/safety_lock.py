from __future__ import annotations

from dataclasses import dataclass
import math


KILIT_ACIK = "İşleme Açık"
KILITLI = "İşlem Kilitli"


class SafetyLockError(Exception):
    """Yeni işlem güvenlik değerlendirmesi üretilemediğinde kullanılır."""


@dataclass(frozen=True)
class SafetyPolicy:
    """Gerçek veya deneme işlemlerinde uygulanacak temel risk sınırları."""

    max_risk_per_trade_pct: float = 1.0
    min_reward_risk: float = 2.0
    max_position_pct: float = 30.0
    daily_loss_limit_pct: float = 2.0
    weekly_loss_limit_pct: float = 4.0
    max_consecutive_losses: int = 3
    require_stop: bool = True
    block_averaging_down: bool = True
    block_overextended_entry: bool = True

    def __post_init__(self) -> None:
        yuzdeler = (
            self.max_risk_per_trade_pct,
            self.max_position_pct,
            self.daily_loss_limit_pct,
            self.weekly_loss_limit_pct,
        )
        if any(not math.isfinite(deger) or deger <= 0 for deger in yuzdeler):
            raise ValueError("Güvenlik yüzdeleri sıfırdan büyük olmalıdır.")
        if not math.isfinite(self.min_reward_risk) or self.min_reward_risk <= 0:
            raise ValueError("Minimum risk/getiri sıfırdan büyük olmalıdır.")
        if self.max_consecutive_losses < 1:
            raise ValueError("Azami ardışık zarar en az 1 olmalıdır.")


@dataclass(frozen=True)
class SafetyLockContext:
    """İşlem günlüğünden türetilen güncel kayıp ve seri bilgisi."""

    daily_net_pnl: float = 0.0
    weekly_net_pnl: float = 0.0
    consecutive_losses: int = 0

    def __post_init__(self) -> None:
        if self.consecutive_losses < 0:
            raise ValueError("Ardışık zarar sayısı negatif olamaz.")
        if not math.isfinite(self.daily_net_pnl):
            raise ValueError("Günlük sonuç sonlu olmalıdır.")
        if not math.isfinite(self.weekly_net_pnl):
            raise ValueError("Haftalık sonuç sonlu olmalıdır.")


@dataclass(frozen=True)
class TradeProposal:
    """Yeni uzun işlem için güvenlik ön kontrol girdileri."""

    symbol: str
    capital: float
    entry_price: float
    quantity: int
    stop_loss: float | None
    target_price: float | None
    averaging_down: bool = False
    overextended_entry: bool = False

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not symbol:
            raise ValueError("Hisse sembolü boş olamaz.")
        if not symbol.endswith(".IS"):
            symbol += ".IS"
        object.__setattr__(self, "symbol", symbol)

        if not math.isfinite(self.capital) or self.capital <= 0:
            raise ValueError("Sermaye sıfırdan büyük olmalıdır.")
        if not math.isfinite(self.entry_price) or self.entry_price <= 0:
            raise ValueError("Giriş fiyatı sıfırdan büyük olmalıdır.")
        if self.quantity < 1:
            raise ValueError("Lot sayısı en az 1 olmalıdır.")
        for ad, deger in (
            ("Stop", self.stop_loss),
            ("Hedef", self.target_price),
        ):
            if deger is not None and (not math.isfinite(deger) or deger <= 0):
                raise ValueError(f"{ad} fiyatı sıfırdan büyük olmalıdır.")

    @property
    def position_amount(self) -> float:
        return self.entry_price * self.quantity

    @property
    def position_pct(self) -> float:
        return self.position_amount / self.capital * 100.0

    @property
    def risk_amount(self) -> float | None:
        if self.stop_loss is None or self.stop_loss >= self.entry_price:
            return None
        return (self.entry_price - self.stop_loss) * self.quantity

    @property
    def risk_pct(self) -> float | None:
        if self.risk_amount is None:
            return None
        return self.risk_amount / self.capital * 100.0

    @property
    def reward_risk(self) -> float | None:
        if (
            self.stop_loss is None
            or self.target_price is None
            or self.stop_loss >= self.entry_price
            or self.target_price <= self.entry_price
        ):
            return None
        risk = self.entry_price - self.stop_loss
        reward = self.target_price - self.entry_price
        return reward / risk


@dataclass(frozen=True)
class SafetyDecision:
    """Yeni işlem için güvenlik kilidi sonucu."""

    status: str
    allowed: bool
    blocking_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    position_amount: float
    position_pct: float
    risk_amount: float | None
    risk_pct: float | None
    reward_risk: float | None
    daily_loss_pct: float
    weekly_loss_pct: float


def evaluate_trade_safety(
    proposal: TradeProposal,
    context: SafetyLockContext | None = None,
    policy: SafetyPolicy | None = None,
) -> SafetyDecision:
    """Yeni işlem teklifini disiplin ve portföy kayıp sınırlarıyla değerlendirir."""

    context = context or SafetyLockContext()
    policy = policy or SafetyPolicy()
    blocks: list[str] = []
    warnings: list[str] = []

    if proposal.position_pct > policy.max_position_pct + 1e-9:
        blocks.append(
            "Pozisyon büyüklüğü sermayenin "
            f"%{proposal.position_pct:.2f}'si; sınır %{policy.max_position_pct:.2f}."
        )

    if proposal.stop_loss is None:
        if policy.require_stop:
            blocks.append("Stop-loss tanımlanmadan yeni işlem açılamaz.")
        else:
            warnings.append("Stop-loss tanımlanmamış.")
    elif proposal.stop_loss >= proposal.entry_price:
        blocks.append("Uzun işlemde stop fiyatı giriş fiyatının altında olmalıdır.")

    if proposal.target_price is None:
        blocks.append("Hedef olmadan risk/getiri oranı doğrulanamaz.")
    elif proposal.target_price <= proposal.entry_price:
        blocks.append("Uzun işlemde hedef fiyat giriş fiyatının üzerinde olmalıdır.")

    if proposal.risk_pct is not None and proposal.risk_pct > policy.max_risk_per_trade_pct + 1e-9:
        blocks.append(
            "Planlanan işlem riski sermayenin "
            f"%{proposal.risk_pct:.2f}'si; sınır %{policy.max_risk_per_trade_pct:.2f}."
        )

    if proposal.reward_risk is not None and proposal.reward_risk + 1e-9 < policy.min_reward_risk:
        blocks.append(
            f"Risk/getiri 1:{proposal.reward_risk:.2f}; "
            f"minimum 1:{policy.min_reward_risk:.2f}."
        )

    daily_loss_pct = max(0.0, -context.daily_net_pnl / proposal.capital * 100.0)
    weekly_loss_pct = max(0.0, -context.weekly_net_pnl / proposal.capital * 100.0)

    if daily_loss_pct >= policy.daily_loss_limit_pct - 1e-9:
        blocks.append(
            f"Günlük zarar %{daily_loss_pct:.2f}; "
            f"günlük sınır %{policy.daily_loss_limit_pct:.2f} doldu."
        )
    if weekly_loss_pct >= policy.weekly_loss_limit_pct - 1e-9:
        blocks.append(
            f"Haftalık zarar %{weekly_loss_pct:.2f}; "
            f"haftalık sınır %{policy.weekly_loss_limit_pct:.2f} doldu."
        )
    if context.consecutive_losses >= policy.max_consecutive_losses:
        blocks.append(
            f"Ardışık {context.consecutive_losses} zarar var; "
            f"izin verilen üst sınır {policy.max_consecutive_losses}."
        )

    if proposal.averaging_down:
        mesaj = "Kaybeden pozisyona ekleme güvenlik kuralını ihlal ediyor."
        (blocks if policy.block_averaging_down else warnings).append(mesaj)
    if proposal.overextended_entry:
        mesaj = "Aşırı yükselmiş hissede yeni giriş işaretlendi."
        (blocks if policy.block_overextended_entry else warnings).append(mesaj)

    allowed = not blocks
    return SafetyDecision(
        status=KILIT_ACIK if allowed else KILITLI,
        allowed=allowed,
        blocking_reasons=tuple(blocks),
        warnings=tuple(warnings),
        position_amount=proposal.position_amount,
        position_pct=proposal.position_pct,
        risk_amount=proposal.risk_amount,
        risk_pct=proposal.risk_pct,
        reward_risk=proposal.reward_risk,
        daily_loss_pct=daily_loss_pct,
        weekly_loss_pct=weekly_loss_pct,
    )
