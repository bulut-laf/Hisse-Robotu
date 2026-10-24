from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .divergence_analysis import (
    DivergenceKind,
    TimeframeDivergenceResult,
)
from .technical_confirmation import (
    NEGATIF,
    NOTR,
    POZITIF,
    MultiTimeframeTechnicalConfirmation,
)
from .trade_plan import ISLEM_VAR, TradePlan


class DecisionClass(str, Enum):
    WATCH_WORTHY = "İzlemeye Değer"
    CAUTIOUS_WATCH = "Temkinli İzle"
    NOT_SUITABLE = "Uygun Değil"


class MatrixDirection(str, Enum):
    POSITIVE = "Olumlu"
    NEUTRAL = "Nötr"
    NEGATIVE = "Olumsuz"
    UNAVAILABLE = "Veri Yok"


@dataclass(frozen=True)
class DecisionMatrixContext:
    market_regime: str | None = None
    sector_outlook: str | None = None
    relative_strength: str | None = None


@dataclass(frozen=True)
class DecisionMatrixRow:
    component: str
    daily: str
    weekly: str
    direction: MatrixDirection
    weight: int
    contribution: int
    explanation: str


@dataclass(frozen=True)
class TechnicalDecisionMatrix:
    symbol: str
    classification: DecisionClass
    quality_score: int
    positive_reasons: tuple[str, ...]
    negative_reasons: tuple[str, ...]
    rows: tuple[DecisionMatrixRow, ...]
    disclaimer: str = (
        "Karar matrisi alım veya satım tavsiyesi üretmez. "
        "Göstergeleri günlük ve haftalık ölçekte açıklanabilir biçimde "
        "bir araya getirir."
    )


def _direction_from_text(value: str | None) -> MatrixDirection:
    normalized = (value or "").strip().casefold()
    if not normalized:
        return MatrixDirection.UNAVAILABLE

    positive_terms = (
        "pozitif",
        "olumlu",
        "yükseliş",
        "güçlü",
        "uygun",
    )
    negative_terms = (
        "negatif",
        "olumsuz",
        "düşüş",
        "riskli",
        "zayıf",
    )

    if any(term in normalized for term in positive_terms):
        return MatrixDirection.POSITIVE
    if any(term in normalized for term in negative_terms):
        return MatrixDirection.NEGATIVE
    return MatrixDirection.NEUTRAL


def _contribution(direction: MatrixDirection, weight: int) -> int:
    if direction == MatrixDirection.POSITIVE:
        return weight
    if direction == MatrixDirection.NEUTRAL:
        return round(weight * 0.45)
    if direction == MatrixDirection.UNAVAILABLE:
        return round(weight * 0.25)
    return 0


def _latest_divergence_direction(
    result: TimeframeDivergenceResult,
) -> MatrixDirection:
    if not result.signals:
        return MatrixDirection.NEUTRAL

    latest = max(
        result.signals,
        key=lambda signal: (
            signal.second.timestamp,
            signal.confidence_score,
        ),
    )
    if latest.kind in {
        DivergenceKind.NORMAL_POSITIVE,
        DivergenceKind.HIDDEN_POSITIVE,
    }:
        return MatrixDirection.POSITIVE
    return MatrixDirection.NEGATIVE


def _divergence_label(
    result: TimeframeDivergenceResult,
) -> str:
    if not result.signals:
        return "Belirgin uyumsuzluk yok"
    latest = max(
        result.signals,
        key=lambda signal: (
            signal.second.timestamp,
            signal.confidence_score,
        ),
    )
    return (
        f"{latest.oscillator} · {latest.kind.value} · "
        f"{latest.confidence_level}"
    )


def _risk_reward_direction(plan: TradePlan) -> MatrixDirection:
    ratios = [
        value
        for value in (plan.risk_odul_1, plan.risk_odul_2)
        if value is not None
    ]
    if not ratios:
        return MatrixDirection.NEGATIVE
    best = max(float(value) for value in ratios)
    if best >= 2.0:
        return MatrixDirection.POSITIVE
    if best >= 1.5:
        return MatrixDirection.NEUTRAL
    return MatrixDirection.NEGATIVE


def _risk_reward_label(plan: TradePlan) -> str:
    values = [
        float(value)
        for value in (plan.risk_odul_1, plan.risk_odul_2)
        if value is not None
    ]
    if not values:
        return "Plan üretilemedi"
    return f"En iyi oran 1:{max(values):.2f}"


def _volatility_direction(plan: TradePlan) -> MatrixDirection:
    atr = float(plan.atr_yuzde)
    if 1.0 <= atr <= 4.5:
        return MatrixDirection.POSITIVE
    if 0.6 <= atr < 1.0 or 4.5 < atr <= 6.0:
        return MatrixDirection.NEUTRAL
    return MatrixDirection.NEGATIVE


def _row(
    component: str,
    daily: str,
    weekly: str,
    direction: MatrixDirection,
    weight: int,
    explanation: str,
) -> DecisionMatrixRow:
    return DecisionMatrixRow(
        component=component,
        daily=daily,
        weekly=weekly,
        direction=direction,
        weight=weight,
        contribution=_contribution(direction, weight),
        explanation=explanation,
    )


def build_technical_decision_matrix(
    technical: MultiTimeframeTechnicalConfirmation,
    plan: TradePlan,
    daily_divergence: TimeframeDivergenceResult,
    weekly_divergence: TimeframeDivergenceResult,
    *,
    context: DecisionMatrixContext | None = None,
) -> TechnicalDecisionMatrix:
    if technical.sembol != plan.sembol:
        raise ValueError(
            "Teknik analiz ve işlem planı aynı sembole ait olmalıdır."
        )

    context = context or DecisionMatrixContext()

    trend_direction = _direction_from_text(
        f"{technical.gunluk.yon} {technical.haftalik.yon}"
    )
    momentum_direction = _direction_from_text(
        f"{technical.gunluk.momentum.durum} "
        f"{technical.haftalik.momentum.durum}"
    )

    daily_volume = technical.gunluk.kirilim.hacim_teyidi
    weekly_volume = technical.haftalik.kirilim.hacim_teyidi
    if daily_volume and weekly_volume:
        volume_direction = MatrixDirection.POSITIVE
    elif daily_volume or weekly_volume:
        volume_direction = MatrixDirection.NEUTRAL
    else:
        volume_direction = MatrixDirection.NEGATIVE

    daily_div_direction = _latest_divergence_direction(daily_divergence)
    weekly_div_direction = _latest_divergence_direction(weekly_divergence)
    if daily_div_direction == weekly_div_direction:
        divergence_direction = daily_div_direction
    elif MatrixDirection.NEGATIVE in {
        daily_div_direction,
        weekly_div_direction,
    }:
        divergence_direction = MatrixDirection.NEUTRAL
    else:
        divergence_direction = MatrixDirection.NEUTRAL

    support_resistance_direction = MatrixDirection.NEUTRAL
    if (
        technical.gunluk.destek is not None
        and technical.gunluk.direnc is not None
    ):
        close = float(technical.gunluk.kapanis)
        support_distance = (
            close - float(technical.gunluk.destek)
        ) / close
        resistance_distance = (
            float(technical.gunluk.direnc) - close
        ) / close
        if support_distance >= 0 and resistance_distance > support_distance:
            support_resistance_direction = MatrixDirection.POSITIVE
        elif resistance_distance <= 0:
            support_resistance_direction = MatrixDirection.NEGATIVE

    market_direction = _direction_from_text(context.market_regime)
    sector_direction = _direction_from_text(context.sector_outlook)
    relative_direction = _direction_from_text(context.relative_strength)
    risk_reward_direction = _risk_reward_direction(plan)
    volatility_direction = _volatility_direction(plan)

    rows = (
        _row(
            "Trend yapısı",
            f"{technical.gunluk.yon} · {technical.gunluk.skor}/100",
            f"{technical.haftalik.yon} · {technical.haftalik.skor}/100",
            trend_direction,
            20,
            "Haftalık ana trend ile günlük yön birlikte değerlendirilir.",
        ),
        _row(
            "Momentum",
            technical.gunluk.momentum.durum,
            technical.haftalik.momentum.durum,
            momentum_direction,
            15,
            "RSI ve MACD histogram ortak momentum görünümüdür.",
        ),
        _row(
            "Hacim teyidi",
            "Var" if daily_volume else "Yok",
            "Var" if weekly_volume else "Yok",
            volume_direction,
            10,
            "Günlük ve haftalık kırılım hacmi ayrı kontrol edilir.",
        ),
        _row(
            "RSI/MACD uyumsuzluk",
            _divergence_label(daily_divergence),
            _divergence_label(weekly_divergence),
            divergence_direction,
            10,
            "En güncel teyit edilmiş uyumsuzluk dikkate alınır.",
        ),
        _row(
            "Destek/direnç konumu",
            (
                f"Destek {technical.gunluk.destek:.2f} · "
                f"Direnç {technical.gunluk.direnc:.2f}"
                if technical.gunluk.destek is not None
                and technical.gunluk.direnc is not None
                else "Seviye yetersiz"
            ),
            (
                f"Destek {technical.haftalik.destek:.2f} · "
                f"Direnç {technical.haftalik.direnc:.2f}"
                if technical.haftalik.destek is not None
                and technical.haftalik.direnc is not None
                else "Seviye yetersiz"
            ),
            support_resistance_direction,
            10,
            "Fiyatın günlük destek ve direnç arasındaki konumu kullanılır.",
        ),
        _row(
            "Volatilite/ATR riski",
            f"ATR %{plan.atr_yuzde:.2f}",
            "Günlük ATR temelli",
            volatility_direction,
            10,
            "Aşırı düşük veya aşırı yüksek volatilite kaliteyi azaltır.",
        ),
        _row(
            "Risk/getiri uygunluğu",
            _risk_reward_label(plan),
            plan.plan_tipi,
            risk_reward_direction,
            15,
            "Mümkün olan hedeflerdeki en iyi risk/getiri oranı kullanılır.",
        ),
        _row(
            "Piyasa rejimi",
            context.market_regime or "Bağlam aktarılmadı",
            "Bağlam aktarılmadı",
            market_direction,
            4,
            "Piyasa rejimi yalnızca mevcutsa matrise eklenir.",
        ),
        _row(
            "Sektör görünümü",
            context.sector_outlook or "Bağlam aktarılmadı",
            "Bağlam aktarılmadı",
            sector_direction,
            3,
            "Sektör görünümü mevcut değilse düşük katkıyla işaretlenir.",
        ),
        _row(
            "Göreceli güç",
            context.relative_strength or "Bağlam aktarılmadı",
            "Bağlam aktarılmadı",
            relative_direction,
            3,
            "Göreceli güç mevcut değilse sonuç tahmin edilmez.",
        ),
    )

    score = sum(row.contribution for row in rows)

    hard_negative = (
        technical.haftalik.yon == NEGATIF
        or technical.gunluk.yon == NEGATIF
        or plan.karar != ISLEM_VAR
        or risk_reward_direction == MatrixDirection.NEGATIVE
    )

    if hard_negative or score < 45:
        classification = DecisionClass.NOT_SUITABLE
    elif (
        score >= 70
        and technical.haftalik.yon == POZITIF
        and technical.gunluk.yon == POZITIF
    ):
        classification = DecisionClass.WATCH_WORTHY
    else:
        classification = DecisionClass.CAUTIOUS_WATCH

    positive_reasons = tuple(
        row.explanation
        for row in rows
        if row.direction == MatrixDirection.POSITIVE
    )
    negative_reasons = tuple(
        row.explanation
        for row in rows
        if row.direction == MatrixDirection.NEGATIVE
    )

    return TechnicalDecisionMatrix(
        symbol=technical.sembol,
        classification=classification,
        quality_score=int(score),
        positive_reasons=positive_reasons,
        negative_reasons=negative_reasons,
        rows=rows,
    )


def decision_matrix_rows(
    matrix: TechnicalDecisionMatrix,
) -> list[dict[str, object]]:
    return [
        {
            "Bileşen": row.component,
            "Günlük": row.daily,
            "Haftalık": row.weekly,
            "Yön": row.direction.value,
            "Ağırlık": row.weight,
            "Katkı": row.contribution,
            "Açıklama": row.explanation,
        }
        for row in matrix.rows
    ]
