from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import floor
from typing import Iterable, Sequence

import pandas as pd

from backend.app.prebreakout.prebreakout_candidate_lifecycle import (
    CandidatePriceObservation,
)
from backend.app.prebreakout.prebreakout_live_watch import PreBreakoutLiveSignal


class PaperTradeStatus(str, Enum):
    ACIK = "AÇIK"
    HEDEF = "HEDEF"
    STOP = "STOP"
    SURE_SONU = "SÜRE SONU"


@dataclass(frozen=True)
class PaperPortfolioConfig:
    initial_capital: float = 100_000.0
    risk_per_trade_pct: float = 1.0
    stop_loss_pct: float = 5.0
    target_return_pct: float = 10.0
    transaction_cost_pct: float = 0.10
    slippage_pct: float = 0.10
    maximum_holding_sessions: int = 20
    maximum_open_positions: int = 10

    def __post_init__(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("Başlangıç sermayesi pozitif olmalıdır.")
        if not 0 < self.risk_per_trade_pct <= 100:
            raise ValueError("İşlem başına risk yüzde 0–100 aralığında olmalıdır.")
        if not 0 < self.stop_loss_pct < 100:
            raise ValueError("Stop yüzdesi 0–100 aralığında olmalıdır.")
        if self.target_return_pct <= 0:
            raise ValueError("Hedef getirisi pozitif olmalıdır.")
        if self.transaction_cost_pct < 0 or self.slippage_pct < 0:
            raise ValueError("Maliyet ve kayma negatif olamaz.")
        if self.maximum_holding_sessions < 1 or self.maximum_open_positions < 1:
            raise ValueError("Seans ve pozisyon sınırları en az 1 olmalıdır.")


@dataclass(frozen=True)
class PaperTrade:
    signal_id: str
    symbol: str
    signal_date: str
    stage: str
    status: PaperTradeStatus
    entry_price: float
    stop_price: float
    target_price: float
    quantity: int
    invested_amount: float
    risk_amount: float
    exit_date: str | None
    exit_price: float | None
    observed_session_count: int
    gross_pnl: float
    transaction_cost: float
    net_pnl: float
    return_pct: float
    note: str


@dataclass(frozen=True)
class PaperPortfolioSummary:
    total_trade_count: int
    open_trade_count: int
    closed_trade_count: int
    target_count: int
    stop_count: int
    expiry_count: int
    win_rate_pct: float | None
    invested_amount: float
    realized_net_pnl: float
    open_net_pnl: float
    total_net_pnl: float
    portfolio_return_pct: float
    maximum_drawdown_pct: float


def _round(value: float) -> float:
    return round(float(value), 4)


def _execution_entry(signal_close: float, slippage_pct: float) -> float:
    return float(signal_close) * (1.0 + slippage_pct / 100.0)


def _execution_exit(reference_price: float, slippage_pct: float) -> float:
    return float(reference_price) * (1.0 - slippage_pct / 100.0)


def _position_size(entry: float, stop: float, config: PaperPortfolioConfig) -> int:
    risk_budget = config.initial_capital * config.risk_per_trade_pct / 100.0
    per_share_risk = entry - stop
    if per_share_risk <= 0:
        return 0
    by_risk = floor(risk_budget / per_share_risk)
    allocation_cap = config.initial_capital / config.maximum_open_positions
    by_allocation = floor(allocation_cap / entry)
    return max(0, min(by_risk, by_allocation))


def _trade_result(
    signal: PreBreakoutLiveSignal,
    status: PaperTradeStatus,
    entry: float,
    stop: float,
    target: float,
    quantity: int,
    observed_count: int,
    exit_date: str | None,
    exit_reference_price: float,
    config: PaperPortfolioConfig,
    note: str,
) -> PaperTrade:
    exit_price = _execution_exit(exit_reference_price, config.slippage_pct)
    invested = entry * quantity
    gross_pnl = (exit_price - entry) * quantity
    cost_rate = config.transaction_cost_pct / 100.0
    transaction_cost = (invested + exit_price * quantity) * cost_rate
    net_pnl = gross_pnl - transaction_cost
    return PaperTrade(
        signal_id=signal.signal_id,
        symbol=signal.symbol,
        signal_date=signal.signal_date,
        stage=signal.stage,
        status=status,
        entry_price=_round(entry),
        stop_price=_round(stop),
        target_price=_round(target),
        quantity=quantity,
        invested_amount=_round(invested),
        risk_amount=_round((entry - stop) * quantity),
        exit_date=exit_date,
        exit_price=_round(exit_price),
        observed_session_count=observed_count,
        gross_pnl=_round(gross_pnl),
        transaction_cost=_round(transaction_cost),
        net_pnl=_round(net_pnl),
        return_pct=_round(net_pnl * 100.0 / invested) if invested else 0.0,
        note=note,
    )


def deneme_islemini_hesapla(
    signal: PreBreakoutLiveSignal,
    observations: Sequence[CandidatePriceObservation],
    *,
    config: PaperPortfolioConfig = PaperPortfolioConfig(),
) -> PaperTrade:
    signal_day = signal.signal_date
    relevant = tuple(
        sorted(
            (item for item in observations if item.observation_date.isoformat() > signal_day),
            key=lambda item: item.observation_date,
        )
    )[: config.maximum_holding_sessions]

    entry = _execution_entry(signal.close, config.slippage_pct)
    stop = entry * (1.0 - config.stop_loss_pct / 100.0)
    target = entry * (1.0 + config.target_return_pct / 100.0)
    quantity = _position_size(entry, stop, config)
    if quantity < 1:
        raise ValueError("Sermaye ve risk sınırlarıyla en az bir adet pozisyon açılamıyor.")

    for index, item in enumerate(relevant, 1):
        # Aynı seansta iki seviye de görülürse fiyat sırası bilinmediği için stop önce kabul edilir.
        if float(item.low) <= stop:
            return _trade_result(
                signal, PaperTradeStatus.STOP, entry, stop, target, quantity,
                index, item.observation_date.isoformat(), stop, config,
                "Stop seviyesi görüldü; aynı seans hedef de görülmüşse temkinli stop önceliği uygulandı.",
            )
        if float(item.high) >= target:
            return _trade_result(
                signal, PaperTradeStatus.HEDEF, entry, stop, target, quantity,
                index, item.observation_date.isoformat(), target, config,
                "Hedef seviyesi görüldü.",
            )

    if len(relevant) >= config.maximum_holding_sessions:
        last = relevant[-1]
        return _trade_result(
            signal, PaperTradeStatus.SURE_SONU, entry, stop, target, quantity,
            len(relevant), last.observation_date.isoformat(), float(last.close), config,
            "Azami elde tutma süresi sonunda kapanış fiyatıyla sanal çıkış yapıldı.",
        )

    mark = float(relevant[-1].close) if relevant else float(signal.close)
    marked = _trade_result(
        signal, PaperTradeStatus.ACIK, entry, stop, target, quantity,
        len(relevant), None, mark, config,
        "Pozisyon açık; net sonuç son mevcut kapanışla geçici olarak işaretlendi.",
    )
    return marked


def _maximum_drawdown_pct(trades: Sequence[PaperTrade], initial_capital: float) -> float:
    equity = float(initial_capital)
    peak = equity
    maximum_drawdown = 0.0
    for trade in sorted(trades, key=lambda item: (item.exit_date or "9999-12-31", item.signal_id)):
        if trade.status is PaperTradeStatus.ACIK:
            continue
        equity += trade.net_pnl
        peak = max(peak, equity)
        if peak > 0:
            maximum_drawdown = max(maximum_drawdown, (peak - equity) * 100.0 / peak)
    return _round(maximum_drawdown)


def deneme_portfoyu_ozeti(
    trades: Iterable[PaperTrade],
    *,
    initial_capital: float = 100_000.0,
) -> PaperPortfolioSummary:
    items = tuple(trades)
    closed = tuple(item for item in items if item.status is not PaperTradeStatus.ACIK)
    open_items = tuple(item for item in items if item.status is PaperTradeStatus.ACIK)
    targets = sum(item.status is PaperTradeStatus.HEDEF for item in closed)
    realized = sum(item.net_pnl for item in closed)
    open_pnl = sum(item.net_pnl for item in open_items)
    total = realized + open_pnl
    return PaperPortfolioSummary(
        total_trade_count=len(items),
        open_trade_count=len(open_items),
        closed_trade_count=len(closed),
        target_count=targets,
        stop_count=sum(item.status is PaperTradeStatus.STOP for item in closed),
        expiry_count=sum(item.status is PaperTradeStatus.SURE_SONU for item in closed),
        win_rate_pct=_round(targets * 100.0 / len(closed)) if closed else None,
        invested_amount=_round(sum(item.invested_amount for item in items)),
        realized_net_pnl=_round(realized),
        open_net_pnl=_round(open_pnl),
        total_net_pnl=_round(total),
        portfolio_return_pct=_round(total * 100.0 / initial_capital),
        maximum_drawdown_pct=_maximum_drawdown_pct(closed, initial_capital),
    )


def deneme_portfoyunu_tabloya_cevir(trades: Iterable[PaperTrade]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Hisse": item.symbol.removesuffix(".IS"),
                "Sinyal tarihi": item.signal_date,
                "Aşama": item.stage,
                "Durum": item.status.value,
                "Giriş": item.entry_price,
                "Stop": item.stop_price,
                "Hedef": item.target_price,
                "Adet": item.quantity,
                "Yatırılan": item.invested_amount,
                "Risk": item.risk_amount,
                "Çıkış tarihi": item.exit_date,
                "Çıkış": item.exit_price,
                "Net sonuç": item.net_pnl,
                "Net getiri (%)": item.return_pct,
                "İşlem günü": item.observed_session_count,
                "Not": item.note,
            }
            for item in trades
        ]
    )
