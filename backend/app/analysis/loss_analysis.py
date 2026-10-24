from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
import math
from typing import Iterable

from ..history.trade_journal import TradeRecord
from ..risk.safety_lock import SafetyLockContext, SafetyPolicy


@dataclass(frozen=True)
class LossCauseSummary:
    cause: str
    trade_count: int
    total_loss: float
    loss_share_pct: float


@dataclass(frozen=True)
class TradeLossDiagnostic:
    record_id: str
    symbol: str
    exit_date: date
    net_pnl: float
    return_pct: float
    causes: tuple[str, ...]


@dataclass(frozen=True)
class PeriodPnl:
    period: str
    net_pnl: float
    trade_count: int


@dataclass(frozen=True)
class LossAnalysisSummary:
    trade_count: int
    winning_count: int
    losing_count: int
    breakeven_count: int
    net_pnl: float
    gross_profit: float
    gross_loss: float
    win_rate_pct: float
    average_win: float
    average_loss: float
    profit_factor: float | None
    expectancy: float
    max_consecutive_losses: int
    max_drawdown: float
    max_drawdown_pct: float


@dataclass(frozen=True)
class LossAnalysisResult:
    summary: LossAnalysisSummary
    diagnostics: tuple[TradeLossDiagnostic, ...]
    causes: tuple[LossCauseSummary, ...]
    daily_pnl: tuple[PeriodPnl, ...]
    weekly_pnl: tuple[PeriodPnl, ...]
    safety_context: SafetyLockContext
    evaluation_date: date


def analyze_trade_losses(
    records: Iterable[TradeRecord],
    *,
    policy: SafetyPolicy | None = None,
    evaluation_date: date | None = None,
) -> LossAnalysisResult:
    """Tamamlanmış işlemleri performans, kayıp nedeni ve kilit bağlamıyla özetler."""

    policy = policy or SafetyPolicy()
    ordered = tuple(sorted(records, key=lambda x: (x.exit_date, x.created_at, x.record_id)))
    evaluation_date = evaluation_date or (ordered[-1].exit_date if ordered else date.today())

    wins = tuple(item for item in ordered if item.net_pnl > 1e-9)
    losses = tuple(item for item in ordered if item.net_pnl < -1e-9)
    breakeven = tuple(item for item in ordered if abs(item.net_pnl) <= 1e-9)
    gross_profit = sum(item.net_pnl for item in wins)
    gross_loss = -sum(item.net_pnl for item in losses)
    net_pnl = sum(item.net_pnl for item in ordered)
    average_win = gross_profit / len(wins) if wins else 0.0
    average_loss = gross_loss / len(losses) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
    expectancy = net_pnl / len(ordered) if ordered else 0.0
    max_streak = _max_consecutive_losses(ordered)
    max_drawdown, max_drawdown_pct = _max_drawdown(ordered)

    diagnostics: list[TradeLossDiagnostic] = []
    cause_counts: Counter[str] = Counter()
    cause_losses: defaultdict[str, float] = defaultdict(float)
    for item in losses:
        causes = _loss_causes(item, policy)
        diagnostics.append(
            TradeLossDiagnostic(
                record_id=item.record_id,
                symbol=item.symbol,
                exit_date=item.exit_date,
                net_pnl=item.net_pnl,
                return_pct=item.return_pct,
                causes=causes,
            )
        )
        allocation = -item.net_pnl / len(causes)
        for cause in causes:
            cause_counts[cause] += 1
            cause_losses[cause] += allocation

    cause_summaries = tuple(
        LossCauseSummary(
            cause=cause,
            trade_count=count,
            total_loss=cause_losses[cause],
            loss_share_pct=(cause_losses[cause] / gross_loss * 100.0 if gross_loss > 0 else 0.0),
        )
        for cause, count in sorted(
            cause_counts.items(),
            key=lambda pair: (-cause_losses[pair[0]], -pair[1], pair[0]),
        )
    )

    daily = _period_pnl(ordered, weekly=False)
    weekly = _period_pnl(ordered, weekly=True)
    context = _safety_context(ordered, evaluation_date)

    return LossAnalysisResult(
        summary=LossAnalysisSummary(
            trade_count=len(ordered),
            winning_count=len(wins),
            losing_count=len(losses),
            breakeven_count=len(breakeven),
            net_pnl=net_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            win_rate_pct=(len(wins) / len(ordered) * 100.0 if ordered else 0.0),
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            max_consecutive_losses=max_streak,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
        ),
        diagnostics=tuple(diagnostics),
        causes=cause_summaries,
        daily_pnl=daily,
        weekly_pnl=weekly,
        safety_context=context,
        evaluation_date=evaluation_date,
    )


def journal_table(records: Iterable[TradeRecord]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "ID": item.record_id,
            "Hesap": item.account_type,
            "Sembol": item.symbol.removesuffix(".IS"),
            "Giriş": item.entry_date.isoformat(),
            "Çıkış": item.exit_date.isoformat(),
            "Giriş fiyatı": round(item.entry_price, 4),
            "Çıkış fiyatı": round(item.exit_price, 4),
            "Lot": item.quantity,
            "Net K/Z": round(item.net_pnl, 2),
            "Getiri %": round(item.return_pct, 2),
            "Plan risk %": None if item.planned_risk_pct is None else round(item.planned_risk_pct, 2),
            "Plan R/R": None if item.planned_reward_risk is None else round(item.planned_reward_risk, 2),
            "Sinyal": item.signal_class,
        }
        for item in sorted(records, key=lambda x: (x.exit_date, x.created_at), reverse=True)
    )


def diagnostic_table(result: LossAnalysisResult) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Sembol": item.symbol.removesuffix(".IS"),
            "Çıkış tarihi": item.exit_date.isoformat(),
            "Net zarar": round(item.net_pnl, 2),
            "Getiri %": round(item.return_pct, 2),
            "Olası nedenler": " | ".join(item.causes),
        }
        for item in result.diagnostics
    )


def cause_table(result: LossAnalysisResult) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "Kayıp nedeni": item.cause,
            "İşlem sayısı": item.trade_count,
            "Paylaştırılmış zarar": round(item.total_loss, 2),
            "Toplam zarardaki pay %": round(item.loss_share_pct, 2),
        }
        for item in result.causes
    )


def _loss_causes(record: TradeRecord, policy: SafetyPolicy) -> tuple[str, ...]:
    causes: list[str] = []
    if record.stop_loss is None:
        causes.append("Stop tanımlanmamış")
    elif record.stop_loss >= record.entry_price:
        causes.append("Stop seviyesi geçersiz")
    elif record.exit_price < record.stop_loss * 0.995:
        causes.append("Çıkış stop seviyesinin altında gerçekleşmiş")

    rr = record.planned_reward_risk
    if rr is None:
        causes.append("Risk/getiri planı hesaplanmamış")
    elif rr < policy.min_reward_risk:
        causes.append("Risk/getiri oranı yetersiz")

    risk_pct = record.planned_risk_pct
    if risk_pct is not None and risk_pct > policy.max_risk_per_trade_pct + 1e-9:
        causes.append("İşlem başına risk sınırı aşılmış")
    if record.position_pct > policy.max_position_pct + 1e-9:
        causes.append("Pozisyon sermaye sınırı aşılmış")
    if record.late_entry:
        causes.append("Geç giriş işaretlenmiş")
    if record.averaging_down:
        causes.append("Kaybeden pozisyona ekleme yapılmış")
    if record.overextended_entry:
        causes.append("Aşırı yükselmiş bölgede giriş yapılmış")
    if not record.signal_class.strip():
        causes.append("Sinyal sınıfı kaydedilmemiş")
    if not causes:
        causes.append("Belirgin kural ihlali yok; strateji/piyasa başarısızlığı")
    return tuple(causes)


def _max_consecutive_losses(records: tuple[TradeRecord, ...]) -> int:
    current = 0
    maximum = 0
    for item in records:
        if item.net_pnl < -1e-9:
            current += 1
            maximum = max(maximum, current)
        elif item.net_pnl > 1e-9:
            current = 0
    return maximum


def _ending_consecutive_losses(records: tuple[TradeRecord, ...], evaluation_date: date) -> int:
    current = 0
    for item in reversed(tuple(x for x in records if x.exit_date <= evaluation_date)):
        if item.net_pnl < -1e-9:
            current += 1
        elif item.net_pnl > 1e-9:
            break
    return current


def _max_drawdown(records: tuple[TradeRecord, ...]) -> tuple[float, float]:
    if not records:
        return 0.0, 0.0
    start_capital = max(records[0].capital_at_entry, 1.0)
    equity = start_capital
    peak = equity
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    for item in records:
        equity += item.net_pnl
        peak = max(peak, equity)
        drawdown = peak - equity
        drawdown_pct = drawdown / peak * 100.0 if peak > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)
    return max_drawdown, max_drawdown_pct


def _period_pnl(records: tuple[TradeRecord, ...], *, weekly: bool) -> tuple[PeriodPnl, ...]:
    grouped: defaultdict[str, list[TradeRecord]] = defaultdict(list)
    for item in records:
        if weekly:
            monday = item.exit_date - timedelta(days=item.exit_date.weekday())
            key = monday.isoformat()
        else:
            key = item.exit_date.isoformat()
        grouped[key].append(item)
    return tuple(
        PeriodPnl(
            period=key,
            net_pnl=sum(item.net_pnl for item in items),
            trade_count=len(items),
        )
        for key, items in sorted(grouped.items())
    )


def _safety_context(records: tuple[TradeRecord, ...], evaluation_date: date) -> SafetyLockContext:
    week_start = evaluation_date - timedelta(days=evaluation_date.weekday())
    week_end = week_start + timedelta(days=6)
    daily = sum(item.net_pnl for item in records if item.exit_date == evaluation_date)
    weekly = sum(item.net_pnl for item in records if week_start <= item.exit_date <= week_end)
    return SafetyLockContext(
        daily_net_pnl=daily,
        weekly_net_pnl=weekly,
        consecutive_losses=_ending_consecutive_losses(records, evaluation_date),
    )
