from __future__ import annotations

from dataclasses import dataclass

from ..data.fundamental_score_store import StoredFundamentalScore


@dataclass(frozen=True)
class FundamentalScoreChange:
    symbol: str
    current_period: str
    previous_period: str
    total_change: int
    profitability_change: int
    growth_change: int
    leverage_change: int
    liquidity_change: int
    cash_flow_change: int
    improving_components: tuple[str, ...]
    weakening_components: tuple[str, ...]


def calculate_score_change(
    current: StoredFundamentalScore,
    previous: StoredFundamentalScore,
) -> FundamentalScoreChange:
    if current.symbol != previous.symbol:
        raise ValueError(
            "Skor değişimi aynı şirket için hesaplanmalıdır."
        )
    if current.period_end <= previous.period_end:
        raise ValueError(
            "Güncel skor dönemi önceki dönemden sonra olmalıdır."
        )

    current_score = current.score
    previous_score = previous.score

    if (
        current_score.total_score is None
        or previous_score.total_score is None
    ):
        raise ValueError(
            "Hesaplanamayan temel skorlar karşılaştırılamaz."
        )

    components = {
        "Kârlılık": (
            current_score.profitability.score
            - previous_score.profitability.score
        ),
        "Büyüme": (
            current_score.growth.score
            - previous_score.growth.score
        ),
        "Borçluluk": (
            current_score.leverage.score
            - previous_score.leverage.score
        ),
        "Likidite": (
            current_score.liquidity.score
            - previous_score.liquidity.score
        ),
        "Nakit akışı": (
            current_score.cash_flow.score
            - previous_score.cash_flow.score
        ),
    }

    return FundamentalScoreChange(
        symbol=current.symbol,
        current_period=current.period_key,
        previous_period=previous.period_key,
        total_change=(
            current_score.total_score
            - previous_score.total_score
        ),
        profitability_change=components["Kârlılık"],
        growth_change=components["Büyüme"],
        leverage_change=components["Borçluluk"],
        liquidity_change=components["Likidite"],
        cash_flow_change=components["Nakit akışı"],
        improving_components=tuple(
            name for name, change in components.items() if change > 0
        ),
        weakening_components=tuple(
            name for name, change in components.items() if change < 0
        ),
    )


def latest_score_change(
    history: tuple[StoredFundamentalScore, ...],
) -> FundamentalScoreChange | None:
    if len(history) < 2:
        return None
    return calculate_score_change(history[-1], history[-2])


def history_rows(
    history: tuple[StoredFundamentalScore, ...],
) -> list[dict[str, object]]:
    return [
        {
            "Dönem": item.period_key,
            "Dönem sonu": item.period_end,
            "Toplam skor": item.score.total_score,
            "Kârlılık": item.score.profitability.score,
            "Büyüme": item.score.growth.score,
            "Borçluluk": item.score.leverage.score,
            "Likidite": item.score.liquidity.score,
            "Nakit akışı": item.score.cash_flow.score,
            "Veri kimliği": item.data_identity,
        }
        for item in history
    ]


def comparison_rows(
    scores: tuple[StoredFundamentalScore, ...],
) -> list[dict[str, object]]:
    return [
        {
            "Şirket": item.symbol,
            "Dönem": item.period_key,
            "Dönem sonu": item.period_end,
            "Temel skor": item.score.total_score,
            "Kalite sınıfı": item.score.grade,
            "Kârlılık": item.score.profitability.score,
            "Büyüme": item.score.growth.score,
            "Borçluluk": item.score.leverage.score,
            "Likidite": item.score.liquidity.score,
            "Nakit akışı": item.score.cash_flow.score,
        }
        for item in scores
    ]
