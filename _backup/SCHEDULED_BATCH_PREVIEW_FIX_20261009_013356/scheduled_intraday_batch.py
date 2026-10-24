from __future__ import annotations

from dataclasses import replace

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Iterable
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from backend.app.analysis.close_behavior_evidence import (
    build_close_behavior_evidence,
)
from backend.app.analysis.eod_decision_gate import (
    EodDecision,
    evaluate_eod_decision,
)
from backend.app.analysis.intraday_candidate_validation import (
    IntradayCandidateValidation,
    validate_intraday_candidate,
)
from backend.app.analysis.intraday_data_freshness import (
    IntradayDataFreshness,
    evaluate_intraday_data_freshness,
)
from backend.app.analysis.intraday_movement_evidence import (
    IntradayMovementEvidence,
    build_intraday_movement_evidence,
)
from backend.app.data.delayed_data_pilot import (
    DelayedDataPilotConfig,
    DelayedDataPilotError,
    DelayedDataSnapshot,
    fetch_delayed_snapshot,
    normalize_symbol,
)

ISTANBUL = ZoneInfo("Europe/Istanbul")


@dataclass(frozen=True)
class ScheduledIntradayBatchFailure:
    symbol: str
    error: str


@dataclass(frozen=True)
class ScheduledIntradayBatchResult:
    snapshots: dict[str, DelayedDataSnapshot]
    evidence: dict[str, IntradayMovementEvidence]
    freshness: dict[str, IntradayDataFreshness]
    validation: dict[str, IntradayCandidateValidation]
    failures: tuple[ScheduledIntradayBatchFailure, ...]
    requested_count: int
    eod_decisions: dict[str, EodDecision] = field(default_factory=dict)

    @property
    def successful_count(self) -> int:
        return len(self.snapshots)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def freshness_count(self) -> int:
        return len(self.freshness)

    @property
    def validation_count(self) -> int:
        return len(self.validation)
    @property
    def eod_decision_count(self) -> int:
        return len(self.eod_decisions)

def _symbols(values: Iterable[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()

    for value in values:
        symbol = normalize_symbol(str(value))

        if symbol not in seen:
            seen.add(symbol)
            ordered.append(symbol)

    if not ordered:
        raise ValueError(
            "Scheduled intraday batch icin en az bir sembol gereklidir."
        )

    return tuple(ordered)


def _extract_symbol_frame(
    raw: pd.DataFrame,
    symbol: str,
    *,
    chunk_size: int,
) -> pd.DataFrame:
    if raw is None or raw.empty:
        raise DelayedDataPilotError("Toplu gun ici veri bos.")

    if not isinstance(raw.columns, pd.MultiIndex):
        if chunk_size != 1:
            raise DelayedDataPilotError(
                "Coklu sembol indirmesinde MultiIndex sutunlari bekleniyordu."
            )

        return raw.copy()

    for level in range(raw.columns.nlevels):
        values = {
            str(value)
            for value in raw.columns.get_level_values(level)
        }

        if symbol in values:
            frame = raw.xs(
                symbol,
                axis=1,
                level=level,
                drop_level=True,
            )

            if isinstance(frame, pd.Series):
                frame = frame.to_frame()

            return frame.copy()

    raise DelayedDataPilotError(
        f"{symbol} toplu gun ici indirme sonucunda bulunamadi."
    )


def _download_5m_batch(
    symbols: tuple[str, ...],
    *,
    config: DelayedDataPilotConfig,
    chunk_size: int = 40,
) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}

    for start in range(0, len(symbols), chunk_size):
        chunk = symbols[start : start + chunk_size]

        raw = yf.download(
            tickers=list(chunk),
            period=config.period,
            interval=config.interval,
            auto_adjust=True,
            progress=False,
            threads=True,
            prepost=False,
            timeout=45,
            group_by="ticker",
        )

        for symbol in chunk:
            frames[symbol] = _extract_symbol_frame(
                raw,
                symbol,
                chunk_size=len(chunk),
            )

    return frames


def run_scheduled_intraday_batch(
    symbols: Iterable[str],
    *,
    now: datetime | None = None,
    config: DelayedDataPilotConfig = DelayedDataPilotConfig(),
    chunk_size: int = 40,
) -> ScheduledIntradayBatchResult:
    normalized = _symbols(symbols)

    received_at = now or datetime.now(ISTANBUL)

    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=ISTANBUL)
    else:
        received_at = received_at.astimezone(ISTANBUL)

    snapshots: dict[str, DelayedDataSnapshot] = {}
    evidence: dict[str, IntradayMovementEvidence] = {}
    freshness: dict[str, IntradayDataFreshness] = {}
    validation: dict[str, IntradayCandidateValidation] = {}
    eod_decisions: dict[str, EodDecision] = {}
    failures: list[ScheduledIntradayBatchFailure] = []

    try:
        frames = _download_5m_batch(
            normalized,
            config=config,
            chunk_size=chunk_size,
        )
    except Exception as error:
        return ScheduledIntradayBatchResult(
            snapshots={},
            evidence={},
            freshness={},
            validation={},
            failures=tuple(
                ScheduledIntradayBatchFailure(
                    symbol=symbol,
                    error=f"Toplu gun ici indirme hatasi: {error}",
                )
                for symbol in normalized
            ),
            requested_count=len(normalized),
            eod_decisions={},
        )

    for symbol in normalized:
        try:
            frame = frames[symbol]

            def cached_downloader(**_: object) -> pd.DataFrame:
                return frame

            snapshot = fetch_delayed_snapshot(
                symbol,
                config=config,
                now=received_at,
                downloader=cached_downloader,
            )

            movement_evidence = build_intraday_movement_evidence(
                symbol,
                frame,
            )

            data_freshness = evaluate_intraday_data_freshness(
                snapshot,
            )

            candidate_validation = validate_intraday_candidate(
                movement_evidence,
                data_freshness,
            )

            close_evidence = build_close_behavior_evidence(frame)

            decision = evaluate_eod_decision(
                validation=candidate_validation,
                freshness=data_freshness,
                evidence=movement_evidence,
                close=close_evidence,
            )

            snapshots[symbol] = snapshot
            evidence[symbol] = movement_evidence
            freshness[symbol] = data_freshness
            validation[symbol] = candidate_validation
            eod_decisions[symbol] = decision

        except (
            DelayedDataPilotError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            failures.append(
                ScheduledIntradayBatchFailure(
                    symbol=symbol,
                    error=str(error),
                )
            )

    return ScheduledIntradayBatchResult(
        snapshots=snapshots,
        evidence=evidence,
        freshness=freshness,
        validation=validation,
        failures=tuple(failures),
        requested_count=len(normalized),
        eod_decisions=eod_decisions,
    )

def fetch_scheduled_intraday_batch(
    symbols: Iterable[str],
    *,
    now: datetime | None = None,
    config: DelayedDataPilotConfig = DelayedDataPilotConfig(),
    chunk_size: int = 40,
    downloader: Callable[..., pd.DataFrame] = yf.download,
) -> ScheduledIntradayBatchResult:
    """Fetch delayed intraday snapshots and read-only movement evidence.

    This remains a data adapter only. It has no ranking, profile, scanner,
    signal, AL/SAT, or persistence authority.
    """

    normalized = _symbols(symbols)

    if chunk_size < 1:
        raise ValueError("chunk_size en az 1 olmalidir.")

    received_at = now or datetime.now(ISTANBUL)

    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=ISTANBUL)
    else:
        received_at = received_at.astimezone(ISTANBUL)

    snapshots: dict[str, DelayedDataSnapshot] = {}
    evidence: dict[str, IntradayMovementEvidence] = {}
    freshness: dict[str, IntradayDataFreshness] = {}
    validation: dict[str, IntradayCandidateValidation] = {}
    failures: list[ScheduledIntradayBatchFailure] = []

    for start in range(0, len(normalized), chunk_size):
        chunk = normalized[start : start + chunk_size]

        try:
            raw = downloader(
                tickers=list(chunk),
                period=config.period,
                interval=config.interval,
                auto_adjust=True,
                progress=False,
                threads=True,
                prepost=False,
                timeout=45,
                group_by="ticker",
            )
        except Exception as error:
            failures.extend(
                ScheduledIntradayBatchFailure(
                    symbol=symbol,
                    error=f"Toplu gun ici indirme hatasi: {error}",
                )
                for symbol in chunk
            )
            continue

        for symbol in chunk:
            try:
                frame = _extract_symbol_frame(
                    raw,
                    symbol,
                    chunk_size=len(chunk),
                )

                def cached_downloader(**_: object) -> pd.DataFrame:
                    return frame

                snapshot = fetch_delayed_snapshot(
                    symbol,
                    config=config,
                    now=received_at,
                    downloader=cached_downloader,
                )

                movement_evidence = build_intraday_movement_evidence(
                    symbol,
                    frame,
                )

                data_freshness = evaluate_intraday_data_freshness(
                    snapshot,
                )

                candidate_validation = validate_intraday_candidate(
                    movement_evidence,
                    data_freshness,
                )

                snapshots[symbol] = snapshot
                evidence[symbol] = movement_evidence
                freshness[symbol] = data_freshness
                validation[symbol] = candidate_validation

            except (
                DelayedDataPilotError,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                failures.append(
                    ScheduledIntradayBatchFailure(
                        symbol=symbol,
                        error=str(error),
                    )
                )

    return ScheduledIntradayBatchResult(
        snapshots=snapshots,
        evidence=evidence,
        freshness=freshness,
        validation=validation,
        failures=tuple(failures),
        requested_count=len(normalized),
    )




