from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import io
from itertools import product
from typing import Iterable

from .signal_outcome_tracking import SignalOutcome


class WalkForwardCalibrationError(ValueError):
    """Walk-forward kalibrasyonu üretilemedi."""


@dataclass(frozen=True)
class CalibrationParameters:
    minimum_quality_score: int
    minimum_risk_reward: float
    minimum_atr_percent: float
    maximum_atr_percent: float
    require_positive_daily_trend: bool
    require_positive_weekly_trend: bool
    require_positive_momentum: bool
    require_volume_confirmation: bool
    require_positive_divergence: bool


@dataclass(frozen=True)
class WindowMetrics:
    sample_count: int
    positive_close_rate: float | None
    average_return_percent: float | None
    average_mfe_percent: float | None
    average_mae_percent: float | None
    maximum_drawdown_percent: float | None


@dataclass(frozen=True)
class WalkForwardWindowResult:
    window_number: int
    training_start: date
    training_end: date
    validation_start: date
    validation_end: date
    parameters: CalibrationParameters
    training: WindowMetrics
    validation: WindowMetrics
    accepted: bool
    rejection_reason: str


@dataclass(frozen=True)
class ParameterAggregate:
    parameters: CalibrationParameters
    validation_window_count: int
    accepted_window_count: int
    total_validation_samples: int
    average_validation_return_percent: float | None
    average_validation_positive_rate: float | None
    worst_validation_return_percent: float | None
    stability_score: float
    status: str


@dataclass(frozen=True)
class WalkForwardCalibrationResult:
    horizon: int
    windows: tuple[WalkForwardWindowResult, ...]
    aggregates: tuple[ParameterAggregate, ...]
    recommended: tuple[ParameterAggregate, ...]
    warning: str


def _positive_text(value: str) -> bool | None:
    normalized = value.strip().casefold()
    if not normalized:
        return None
    if any(word in normalized for word in ("pozitif", "olumlu", "güçlü")):
        return True
    if any(word in normalized for word in ("negatif", "olumsuz", "zayıf")):
        return False
    return None


def _horizon_return(
    outcome: SignalOutcome,
    horizon: int,
) -> tuple[float, float, float] | None:
    item = next(
        (
            candidate
            for candidate in outcome.horizons
            if candidate.horizon == horizon
            and candidate.available
            and candidate.close_return_percent is not None
            and candidate.maximum_favorable_excursion_percent is not None
            and candidate.maximum_adverse_excursion_percent is not None
        ),
        None,
    )
    if item is None:
        return None
    return (
        float(item.close_return_percent),
        float(item.maximum_favorable_excursion_percent),
        float(item.maximum_adverse_excursion_percent),
    )


def _matches(
    outcome: SignalOutcome,
    parameters: CalibrationParameters,
) -> bool:
    snapshot = outcome.snapshot

    if snapshot.quality_score < parameters.minimum_quality_score:
        return False

    if (
        snapshot.risk_reward_ratio is None
        or snapshot.risk_reward_ratio < parameters.minimum_risk_reward
    ):
        return False

    if (
        snapshot.atr_percent is None
        or snapshot.atr_percent < parameters.minimum_atr_percent
        or snapshot.atr_percent > parameters.maximum_atr_percent
    ):
        return False

    if parameters.require_positive_daily_trend:
        if _positive_text(snapshot.daily_direction) is not True:
            return False

    if parameters.require_positive_weekly_trend:
        if _positive_text(snapshot.weekly_direction) is not True:
            return False

    if parameters.require_positive_momentum:
        if _positive_text(snapshot.momentum_state) is not True:
            return False

    if parameters.require_volume_confirmation:
        if snapshot.volume_confirmation is not True:
            return False

    if parameters.require_positive_divergence:
        if _positive_text(snapshot.divergence_type) is not True:
            return False

    return True


def _maximum_drawdown(returns: list[float]) -> float | None:
    if not returns:
        return None
    equity = 100.0
    peak = equity
    worst = 0.0
    for value in returns:
        equity *= 1.0 + value / 100.0
        peak = max(peak, equity)
        drawdown = (equity / peak - 1.0) * 100.0
        worst = min(worst, drawdown)
    return round(worst, 4)


def _metrics(
    outcomes: Iterable[SignalOutcome],
    *,
    horizon: int,
    parameters: CalibrationParameters,
) -> WindowMetrics:
    returns: list[float] = []
    mfes: list[float] = []
    maes: list[float] = []

    for outcome in outcomes:
        if not _matches(outcome, parameters):
            continue
        values = _horizon_return(outcome, horizon)
        if values is None:
            continue
        close_return, mfe, mae = values
        returns.append(close_return)
        mfes.append(mfe)
        maes.append(mae)

    if not returns:
        return WindowMetrics(
            sample_count=0,
            positive_close_rate=None,
            average_return_percent=None,
            average_mfe_percent=None,
            average_mae_percent=None,
            maximum_drawdown_percent=None,
        )

    return WindowMetrics(
        sample_count=len(returns),
        positive_close_rate=round(
            sum(value > 0 for value in returns) / len(returns) * 100.0,
            2,
        ),
        average_return_percent=round(
            sum(returns) / len(returns),
            4,
        ),
        average_mfe_percent=round(
            sum(mfes) / len(mfes),
            4,
        ),
        average_mae_percent=round(
            sum(maes) / len(maes),
            4,
        ),
        maximum_drawdown_percent=_maximum_drawdown(returns),
    )


def default_parameter_grid() -> tuple[CalibrationParameters, ...]:
    combinations = product(
        (55, 65, 70, 75),
        (1.5, 2.0, 2.5),
        ((0.8, 5.0), (1.0, 4.5), (1.5, 4.0)),
        (False, True),
        (False, True),
        (False, True),
        (False, True),
        (False, True),
    )

    result = []
    for (
        quality,
        risk_reward,
        atr_range,
        daily,
        weekly,
        momentum,
        volume,
        divergence,
    ) in combinations:
        result.append(
            CalibrationParameters(
                minimum_quality_score=quality,
                minimum_risk_reward=risk_reward,
                minimum_atr_percent=atr_range[0],
                maximum_atr_percent=atr_range[1],
                require_positive_daily_trend=daily,
                require_positive_weekly_trend=weekly,
                require_positive_momentum=momentum,
                require_volume_confirmation=volume,
                require_positive_divergence=divergence,
            )
        )
    return tuple(result)


def _objective(metrics: WindowMetrics) -> float:
    if (
        metrics.average_return_percent is None
        or metrics.positive_close_rate is None
        or metrics.maximum_drawdown_percent is None
    ):
        return float("-inf")
    return (
        metrics.average_return_percent * 2.0
        + metrics.positive_close_rate / 10.0
        + metrics.maximum_drawdown_percent * 0.25
    )


def run_walk_forward_calibration(
    outcomes: Iterable[SignalOutcome],
    *,
    horizon: int,
    training_size: int = 40,
    validation_size: int = 15,
    step_size: int = 15,
    minimum_training_samples: int = 8,
    minimum_validation_samples: int = 4,
    parameter_grid: Iterable[CalibrationParameters] | None = None,
) -> WalkForwardCalibrationResult:
    if training_size < 10:
        raise WalkForwardCalibrationError(
            "Eğitim penceresi en az 10 kayıt olmalıdır."
        )
    if validation_size < 5:
        raise WalkForwardCalibrationError(
            "Doğrulama penceresi en az 5 kayıt olmalıdır."
        )
    if step_size < 1:
        raise WalkForwardCalibrationError(
            "Yürüme adımı en az 1 kayıt olmalıdır."
        )
    if minimum_training_samples < 2 or minimum_validation_samples < 2:
        raise WalkForwardCalibrationError(
            "Minimum örnek sayıları en az 2 olmalıdır."
        )

    records = tuple(
        sorted(
            outcomes,
            key=lambda item: (
                item.snapshot.signal_date,
                item.snapshot.record_id,
            ),
        )
    )
    if len(records) < training_size + validation_size:
        raise WalkForwardCalibrationError(
            "Walk-forward için yeterli tamamlanmış kayıt yok."
        )

    grid = tuple(parameter_grid or default_parameter_grid())
    if not grid:
        raise WalkForwardCalibrationError("Parametre ızgarası boş.")

    windows: list[WalkForwardWindowResult] = []
    aggregate_values: dict[
        CalibrationParameters,
        list[WalkForwardWindowResult],
    ] = {item: [] for item in grid}

    window_number = 0
    start = 0
    while start + training_size + validation_size <= len(records):
        training = records[start:start + training_size]
        validation = records[
            start + training_size:
            start + training_size + validation_size
        ]

        candidates: list[
            tuple[float, CalibrationParameters, WindowMetrics]
        ] = []
        for parameters in grid:
            metrics = _metrics(
                training,
                horizon=horizon,
                parameters=parameters,
            )
            if metrics.sample_count < minimum_training_samples:
                continue
            candidates.append(
                (_objective(metrics), parameters, metrics)
            )

        if not candidates:
            start += step_size
            continue

        _, best_parameters, training_metrics = max(
            candidates,
            key=lambda item: item[0],
        )
        validation_metrics = _metrics(
            validation,
            horizon=horizon,
            parameters=best_parameters,
        )

        accepted = True
        rejection_reason = ""
        if validation_metrics.sample_count < minimum_validation_samples:
            accepted = False
            rejection_reason = "Doğrulama örneği yetersiz."
        elif (
            validation_metrics.average_return_percent is None
            or validation_metrics.average_return_percent <= 0
        ):
            accepted = False
            rejection_reason = "Doğrulama ortalama getirisi pozitif değil."
        elif (
            training_metrics.average_return_percent is not None
            and validation_metrics.average_return_percent
            < training_metrics.average_return_percent * 0.25
        ):
            accepted = False
            rejection_reason = (
                "Eğitim başarısı doğrulama döneminde korunmadı."
            )

        window_number += 1
        window_result = WalkForwardWindowResult(
            window_number=window_number,
            training_start=training[0].snapshot.signal_date,
            training_end=training[-1].snapshot.signal_date,
            validation_start=validation[0].snapshot.signal_date,
            validation_end=validation[-1].snapshot.signal_date,
            parameters=best_parameters,
            training=training_metrics,
            validation=validation_metrics,
            accepted=accepted,
            rejection_reason=rejection_reason,
        )
        windows.append(window_result)
        aggregate_values[best_parameters].append(window_result)
        start += step_size

    if not windows:
        raise WalkForwardCalibrationError(
            "Minimum örnek şartlarını geçen walk-forward penceresi yok."
        )

    aggregates: list[ParameterAggregate] = []
    for parameters, parameter_windows in aggregate_values.items():
        if not parameter_windows:
            continue

        valid_returns = [
            item.validation.average_return_percent
            for item in parameter_windows
            if item.validation.average_return_percent is not None
        ]
        valid_rates = [
            item.validation.positive_close_rate
            for item in parameter_windows
            if item.validation.positive_close_rate is not None
        ]

        average_return = (
            None
            if not valid_returns
            else round(sum(valid_returns) / len(valid_returns), 4)
        )
        average_rate = (
            None
            if not valid_rates
            else round(sum(valid_rates) / len(valid_rates), 2)
        )
        worst_return = (
            None if not valid_returns else round(min(valid_returns), 4)
        )
        accepted_count = sum(item.accepted for item in parameter_windows)
        acceptance_ratio = accepted_count / len(parameter_windows)
        return_penalty = (
            0.0
            if average_return is None
            else max(0.0, average_return)
        )
        stability_score = round(
            acceptance_ratio * 70.0
            + min(30.0, return_penalty * 5.0),
            2,
        )

        if stability_score >= 75 and accepted_count >= 2:
            status = "Kararlı bölge"
        elif stability_score >= 50:
            status = "İzlenebilir"
        else:
            status = "Aşırı uyum riski"

        aggregates.append(
            ParameterAggregate(
                parameters=parameters,
                validation_window_count=len(parameter_windows),
                accepted_window_count=accepted_count,
                total_validation_samples=sum(
                    item.validation.sample_count
                    for item in parameter_windows
                ),
                average_validation_return_percent=average_return,
                average_validation_positive_rate=average_rate,
                worst_validation_return_percent=worst_return,
                stability_score=stability_score,
                status=status,
            )
        )

    aggregates.sort(
        key=lambda item: (
            item.stability_score,
            item.average_validation_return_percent
            if item.average_validation_return_percent is not None
            else float("-inf"),
        ),
        reverse=True,
    )
    recommended = tuple(
        item
        for item in aggregates
        if item.status == "Kararlı bölge"
    )[:5]

    warning = (
        "Walk-forward sonucu gelecek performansı garanti etmez. "
        "Tek bir en iyi kombinasyon yerine doğrulama pencerelerinde "
        "tekrarlanan kararlı parametre bölgeleri dikkate alınmalıdır."
    )

    return WalkForwardCalibrationResult(
        horizon=horizon,
        windows=tuple(windows),
        aggregates=tuple(aggregates),
        recommended=recommended,
        warning=warning,
    )


def window_rows(
    result: WalkForwardCalibrationResult,
) -> list[dict[str, object]]:
    rows = []
    for item in result.windows:
        rows.append(
            {
                "Pencere": item.window_number,
                "Eğitim başlangıcı": item.training_start,
                "Eğitim bitişi": item.training_end,
                "Doğrulama başlangıcı": item.validation_start,
                "Doğrulama bitişi": item.validation_end,
                "Kalite eşiği": item.parameters.minimum_quality_score,
                "Risk/getiri eşiği": item.parameters.minimum_risk_reward,
                "ATR alt": item.parameters.minimum_atr_percent,
                "ATR üst": item.parameters.maximum_atr_percent,
                "Günlük trend şartı": item.parameters.require_positive_daily_trend,
                "Haftalık trend şartı": item.parameters.require_positive_weekly_trend,
                "Momentum şartı": item.parameters.require_positive_momentum,
                "Hacim şartı": item.parameters.require_volume_confirmation,
                "Uyumsuzluk şartı": item.parameters.require_positive_divergence,
                "Eğitim örneği": item.training.sample_count,
                "Eğitim getiri (%)": item.training.average_return_percent,
                "Doğrulama örneği": item.validation.sample_count,
                "Doğrulama başarı (%)": item.validation.positive_close_rate,
                "Doğrulama getiri (%)": item.validation.average_return_percent,
                "Doğrulama MFE (%)": item.validation.average_mfe_percent,
                "Doğrulama MAE (%)": item.validation.average_mae_percent,
                "Doğrulama max. düşüş (%)": item.validation.maximum_drawdown_percent,
                "Kabul": "Evet" if item.accepted else "Hayır",
                "Ret gerekçesi": item.rejection_reason,
            }
        )
    return rows


def aggregate_rows(
    result: WalkForwardCalibrationResult,
) -> list[dict[str, object]]:
    rows = []
    for item in result.aggregates:
        rows.append(
            {
                "Kalite eşiği": item.parameters.minimum_quality_score,
                "Risk/getiri eşiği": item.parameters.minimum_risk_reward,
                "ATR alt": item.parameters.minimum_atr_percent,
                "ATR üst": item.parameters.maximum_atr_percent,
                "Günlük trend şartı": item.parameters.require_positive_daily_trend,
                "Haftalık trend şartı": item.parameters.require_positive_weekly_trend,
                "Momentum şartı": item.parameters.require_positive_momentum,
                "Hacim şartı": item.parameters.require_volume_confirmation,
                "Uyumsuzluk şartı": item.parameters.require_positive_divergence,
                "Doğrulama penceresi": item.validation_window_count,
                "Kabul edilen pencere": item.accepted_window_count,
                "Toplam doğrulama örneği": item.total_validation_samples,
                "Ort. doğrulama getiri (%)": item.average_validation_return_percent,
                "Ort. doğrulama başarı (%)": item.average_validation_positive_rate,
                "En kötü doğrulama getiri (%)": item.worst_validation_return_percent,
                "Kararlılık skoru": item.stability_score,
                "Durum": item.status,
            }
        )
    return rows


def calibration_to_csv(
    result: WalkForwardCalibrationResult,
) -> bytes:
    rows = aggregate_rows(result)
    output = io.StringIO()
    fieldnames = list(rows[0]) if rows else ["Durum"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + output.getvalue()).encode("utf-8")
