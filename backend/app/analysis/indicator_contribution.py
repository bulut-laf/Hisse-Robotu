from __future__ import annotations

from dataclasses import dataclass
import csv
import io
from itertools import combinations
from typing import Callable, Iterable

from .signal_outcome_tracking import SignalOutcome


@dataclass(frozen=True)
class IndicatorDefinition:
    name: str
    evaluator: Callable[[SignalOutcome], bool | None]


@dataclass(frozen=True)
class IndicatorContribution:
    horizon: int
    indicator: str
    present_count: int
    absent_count: int
    present_success_rate: float | None
    absent_success_rate: float | None
    success_rate_difference: float | None
    present_average_return: float | None
    absent_average_return: float | None
    average_return_difference: float | None
    confidence: str
    interpretation: str


@dataclass(frozen=True)
class RedundancyFinding:
    first_indicator: str
    second_indicator: str
    comparable_count: int
    agreement_rate: float
    status: str


def _positive_text(value: str) -> bool | None:
    normalized = value.strip().casefold()
    if not normalized:
        return None
    if any(word in normalized for word in ("pozitif", "olumlu", "güçlü")):
        return True
    if any(word in normalized for word in ("negatif", "olumsuz", "zayıf")):
        return False
    return None


def default_indicator_definitions() -> tuple[IndicatorDefinition, ...]:
    return (
        IndicatorDefinition(
            "Günlük trend pozitif",
            lambda outcome: _positive_text(
                outcome.snapshot.daily_direction
            ),
        ),
        IndicatorDefinition(
            "Haftalık trend pozitif",
            lambda outcome: _positive_text(
                outcome.snapshot.weekly_direction
            ),
        ),
        IndicatorDefinition(
            "Momentum pozitif",
            lambda outcome: _positive_text(
                outcome.snapshot.momentum_state
            ),
        ),
        IndicatorDefinition(
            "Hacim teyidi",
            lambda outcome: outcome.snapshot.volume_confirmation,
        ),
        IndicatorDefinition(
            "Pozitif uyumsuzluk",
            lambda outcome: _positive_text(
                outcome.snapshot.divergence_type
            ),
        ),
        IndicatorDefinition(
            "Piyasa rejimi olumlu",
            lambda outcome: _positive_text(
                outcome.snapshot.market_regime
            ),
        ),
        IndicatorDefinition(
            "ATR uygun aralıkta",
            lambda outcome: (
                None
                if outcome.snapshot.atr_percent is None
                else 1.0 <= outcome.snapshot.atr_percent <= 4.5
            ),
        ),
        IndicatorDefinition(
            "Risk/getiri en az 1:2",
            lambda outcome: (
                None
                if outcome.snapshot.risk_reward_ratio is None
                else outcome.snapshot.risk_reward_ratio >= 2.0
            ),
        ),
        IndicatorDefinition(
            "Kalite skoru en az 70",
            lambda outcome: outcome.snapshot.quality_score >= 70,
        ),
    )


def _horizon_item(outcome: SignalOutcome, horizon: int):
    return next(
        (
            item
            for item in outcome.horizons
            if item.horizon == horizon and item.available
        ),
        None,
    )


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _rate(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(value > 0 for value in values) / len(values) * 100, 2)


def analyze_indicator_contributions(
    outcomes: Iterable[SignalOutcome],
    *,
    horizon: int,
    minimum_group_size: int = 5,
    definitions: Iterable[IndicatorDefinition] | None = None,
) -> tuple[IndicatorContribution, ...]:
    if minimum_group_size < 2:
        raise ValueError("Minimum grup büyüklüğü en az 2 olmalıdır.")

    records = tuple(outcomes)
    definitions = tuple(definitions or default_indicator_definitions())
    results: list[IndicatorContribution] = []

    for definition in definitions:
        present: list[float] = []
        absent: list[float] = []

        for outcome in records:
            item = _horizon_item(outcome, horizon)
            if item is None or item.close_return_percent is None:
                continue

            state = definition.evaluator(outcome)
            if state is True:
                present.append(float(item.close_return_percent))
            elif state is False:
                absent.append(float(item.close_return_percent))

        enough = (
            len(present) >= minimum_group_size
            and len(absent) >= minimum_group_size
        )
        present_rate = _rate(present)
        absent_rate = _rate(absent)
        present_average = _average(present)
        absent_average = _average(absent)

        rate_difference = (
            None
            if not enough
            or present_rate is None
            or absent_rate is None
            else round(present_rate - absent_rate, 2)
        )
        return_difference = (
            None
            if not enough
            or present_average is None
            or absent_average is None
            else round(present_average - absent_average, 4)
        )

        if not enough:
            confidence = "Yetersiz örnek"
            interpretation = (
                "Gösterge hakkında sonuç üretmek için her iki grupta da "
                f"en az {minimum_group_size} tamamlanmış kayıt gerekir."
            )
        elif (
            rate_difference is not None
            and return_difference is not None
            and rate_difference >= 10
            and return_difference > 0
        ):
            confidence = "Destekleyici"
            interpretation = (
                "Gösterge mevcutken hem başarı oranı hem ortalama getiri "
                "daha yüksek."
            )
        elif (
            rate_difference is not None
            and return_difference is not None
            and rate_difference <= -10
            and return_difference < 0
        ):
            confidence = "Zayıflatıcı"
            interpretation = (
                "Gösterge mevcutken sonuçlar daha zayıf; ağırlığı yeniden "
                "incelenmelidir."
            )
        else:
            confidence = "Belirsiz"
            interpretation = (
                "Mevcut örneklemde tutarlı ve güçlü bir katkı farkı yok."
            )

        results.append(
            IndicatorContribution(
                horizon=horizon,
                indicator=definition.name,
                present_count=len(present),
                absent_count=len(absent),
                present_success_rate=present_rate,
                absent_success_rate=absent_rate,
                success_rate_difference=rate_difference,
                present_average_return=present_average,
                absent_average_return=absent_average,
                average_return_difference=return_difference,
                confidence=confidence,
                interpretation=interpretation,
            )
        )

    return tuple(results)


def analyze_redundancy(
    outcomes: Iterable[SignalOutcome],
    *,
    minimum_sample_size: int = 10,
    agreement_threshold: float = 0.90,
    definitions: Iterable[IndicatorDefinition] | None = None,
) -> tuple[RedundancyFinding, ...]:
    records = tuple(outcomes)
    definitions = tuple(definitions or default_indicator_definitions())
    findings: list[RedundancyFinding] = []

    for first, second in combinations(definitions, 2):
        pairs: list[tuple[bool, bool]] = []
        for outcome in records:
            first_state = first.evaluator(outcome)
            second_state = second.evaluator(outcome)
            if first_state is None or second_state is None:
                continue
            pairs.append((first_state, second_state))

        if len(pairs) < minimum_sample_size:
            continue

        agreement = sum(left == right for left, right in pairs) / len(pairs)
        if agreement >= agreement_threshold:
            findings.append(
                RedundancyFinding(
                    first_indicator=first.name,
                    second_indicator=second.name,
                    comparable_count=len(pairs),
                    agreement_rate=round(agreement * 100, 2),
                    status="Yüksek benzerlik",
                )
            )

    return tuple(
        sorted(
            findings,
            key=lambda item: item.agreement_rate,
            reverse=True,
        )
    )


def contribution_rows(
    contributions: Iterable[IndicatorContribution],
) -> list[dict[str, object]]:
    return [
        {
            "Ufuk": f"{item.horizon} işlem günü",
            "Gösterge": item.indicator,
            "Mevcut örnek": item.present_count,
            "Yok örnek": item.absent_count,
            "Mevcut başarı (%)": item.present_success_rate,
            "Yok başarı (%)": item.absent_success_rate,
            "Başarı farkı (puan)": item.success_rate_difference,
            "Mevcut ort. getiri (%)": item.present_average_return,
            "Yok ort. getiri (%)": item.absent_average_return,
            "Getiri farkı (%)": item.average_return_difference,
            "Sonuç": item.confidence,
            "Yorum": item.interpretation,
        }
        for item in contributions
    ]


def redundancy_rows(
    findings: Iterable[RedundancyFinding],
) -> list[dict[str, object]]:
    return [
        {
            "Birinci gösterge": item.first_indicator,
            "İkinci gösterge": item.second_indicator,
            "Karşılaştırılabilir kayıt": item.comparable_count,
            "Benzerlik (%)": item.agreement_rate,
            "Durum": item.status,
        }
        for item in findings
    ]


def contribution_to_csv(
    contributions: Iterable[IndicatorContribution],
) -> bytes:
    rows = contribution_rows(contributions)
    output = io.StringIO()
    fieldnames = list(rows[0]) if rows else [
        "Ufuk",
        "Gösterge",
        "Mevcut örnek",
        "Yok örnek",
        "Sonuç",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + output.getvalue()).encode("utf-8")
