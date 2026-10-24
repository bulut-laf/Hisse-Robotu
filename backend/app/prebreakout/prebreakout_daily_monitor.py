from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from backend.app.prebreakout.prebreakout_candidate_lifecycle import (
    CandidateLifecycleConfig,
    CandidateLifecycleRecord,
    CandidatePriceObservation,
    adayin_yasam_dongusunu_degerlendir,
    yasam_dongusu_kaydet,
)
from backend.app.prebreakout.prebreakout_live_performance import (
    LiveSignalPerformance,
    canli_performanslari_kaydet,
    canli_sinyal_performansini_hesapla,
)
from backend.app.prebreakout.prebreakout_live_watch import (
    DEFAULT_LIVE_WATCH_PATH,
    PreBreakoutLiveSignal,
    canli_sinyalleri_kaydet,
    canli_sinyalleri_yukle,
)
from backend.app.prebreakout.prebreakout_models import PreBreakoutResult
from backend.app.prebreakout.prebreakout_paper_portfolio import (
    PaperPortfolioConfig,
    PaperPortfolioSummary,
    PaperTrade,
    deneme_islemini_hesapla,
    deneme_portfoyu_ozeti,
)
from backend.app.prebreakout.prebreakout_threshold_policy import PreBreakoutThresholdPolicy

DEFAULT_DAILY_REPORT_PATH = Path("backend/data/prebreakout_daily_monitor.json")
DEFAULT_PAPER_TRADES_PATH = Path("backend/data/prebreakout_paper_trades.json")


@dataclass(frozen=True)
class DailyMonitorResult:
    run_date: str
    new_signal_count: int
    total_signal_count: int
    lifecycle_records: tuple[CandidateLifecycleRecord, ...]
    performance_records: tuple[LiveSignalPerformance, ...]
    paper_trades: tuple[PaperTrade, ...]
    portfolio_summary: PaperPortfolioSummary
    missing_observation_symbols: tuple[str, ...]


def _observations_for(
    symbol: str,
    observations_by_symbol: Mapping[str, Sequence[CandidatePriceObservation]],
) -> tuple[CandidatePriceObservation, ...]:
    normalized = symbol.upper()
    for key, value in observations_by_symbol.items():
        if key.upper() == normalized:
            return tuple(value)
    return ()


def _paper_trades_save(records: Iterable[PaperTrade], path: str | Path) -> None:
    target = Path(path)
    payload = []
    for record in records:
        row = asdict(record)
        row["status"] = record.status.value
        payload.append(row)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _daily_report_save(result: DailyMonitorResult, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_date": result.run_date,
        "new_signal_count": result.new_signal_count,
        "total_signal_count": result.total_signal_count,
        "lifecycle_count": len(result.lifecycle_records),
        "performance_count": len(result.performance_records),
        "paper_trade_count": len(result.paper_trades),
        "missing_observation_symbols": list(result.missing_observation_symbols),
        "portfolio_summary": asdict(result.portfolio_summary),
    }
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def gunluk_izleme_akisini_calistir(
    results: Iterable[PreBreakoutResult],
    run_date: date,
    policy: PreBreakoutThresholdPolicy,
    observations_by_symbol: Mapping[str, Sequence[CandidatePriceObservation]],
    *,
    live_watch_path: str | Path = DEFAULT_LIVE_WATCH_PATH,
    lifecycle_path: str | Path = "backend/data/prebreakout_candidate_lifecycle.json",
    performance_path: str | Path = "backend/data/prebreakout_live_performance.json",
    paper_trades_path: str | Path = DEFAULT_PAPER_TRADES_PATH,
    daily_report_path: str | Path = DEFAULT_DAILY_REPORT_PATH,
    lifecycle_config: CandidateLifecycleConfig = CandidateLifecycleConfig(),
    portfolio_config: PaperPortfolioConfig = PaperPortfolioConfig(),
) -> DailyMonitorResult:
    """Sprint-99 günlük izleme zincirini tek ve tekrar çalıştırılabilir adımda yürütür."""
    new_signals = canli_sinyalleri_kaydet(
        results,
        run_date,
        policy,
        path=live_watch_path,
        duplicate_cooldown_days=lifecycle_config.duplicate_cooldown_days,
    )
    all_signals = canli_sinyalleri_yukle(live_watch_path)

    lifecycle_records: list[CandidateLifecycleRecord] = []
    performance_records: list[LiveSignalPerformance] = []
    paper_trades: list[PaperTrade] = []
    missing_symbols: set[str] = set()

    for signal in all_signals:
        observations = _observations_for(signal.symbol, observations_by_symbol)
        if not observations:
            missing_symbols.add(signal.symbol)
        lifecycle_records.append(
            adayin_yasam_dongusunu_degerlendir(
                signal,
                observations,
                config=lifecycle_config,
                as_of_date=run_date,
            )
        )
        performance_records.append(
            canli_sinyal_performansini_hesapla(
                signal,
                observations,
                as_of_date=run_date,
            )
        )
        paper_trades.append(
            deneme_islemini_hesapla(
                signal,
                observations,
                config=portfolio_config,
            )
        )

    lifecycle_tuple = tuple(lifecycle_records)
    performance_tuple = tuple(performance_records)
    paper_tuple = tuple(paper_trades)
    portfolio_summary = deneme_portfoyu_ozeti(
        paper_tuple,
        initial_capital=portfolio_config.initial_capital,
    )

    yasam_dongusu_kaydet(lifecycle_tuple, lifecycle_path)
    canli_performanslari_kaydet(performance_tuple, performance_path)
    _paper_trades_save(paper_tuple, paper_trades_path)

    result = DailyMonitorResult(
        run_date=run_date.isoformat(),
        new_signal_count=len(new_signals),
        total_signal_count=len(all_signals),
        lifecycle_records=lifecycle_tuple,
        performance_records=performance_tuple,
        paper_trades=paper_tuple,
        portfolio_summary=portfolio_summary,
        missing_observation_symbols=tuple(sorted(missing_symbols)),
    )
    _daily_report_save(result, daily_report_path)
    return result
