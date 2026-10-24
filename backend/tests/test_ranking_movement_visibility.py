from backend.app.analysis.ranking_memory import RankObservation
from backend.app.analysis.ranking_movement_visibility import (
    build_ranking_movement_rows,
    ranking_movement_table_rows,
)
from backend.app.analysis.ranking_trajectory import build_rank_trajectory


def obs(day, rank, symbol="AAA"):
    return RankObservation(
        as_of=day,
        symbol=symbol,
        rank=rank,
        ranked_universe_size=500,
        universe_source="BIST",
        profile_name="Dengeli",
    )


def test_non_date_observation_is_skipped_without_breaking_history():
    items = (
        obs("Kişisel liste", 300),
        obs("2026-08-20", 220),
        obs("2026-08-21", 150),
        obs("2026-08-22", 90),
        obs("2026-08-23", 40),
    )
    result = build_rank_trajectory(items, "AAA")
    assert result is not None
    assert result.current_rank == 40
    assert result.gain_3s == 180


def test_all_ranked_symbols_get_1s_3s_5s_and_jump_acceleration():
    items = tuple(
        obs(day, rank, symbol)
        for symbol, ranks in (
            ("AAA", (300, 260, 210, 150, 90, 40)),
            ("BBB", (30, 29, 27, 25, 24, 23)),
        )
        for day, rank in zip(
            ("2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-22", "2026-08-23"),
            ranks,
        )
    )
    rows = build_ranking_movement_rows(items)
    assert [row.symbol for row in rows] == ["AAA", "BBB"]
    aaa = rows[0]
    assert aaa.gain_1s == 50
    assert aaa.gain_3s == 170
    assert aaa.gain_5s == 260
    assert aaa.acceleration is not None
    assert aaa.positive_steps_5s == 5
    assert aaa.persistence == "KALICI"
    assert aaa.top5_distance == 35


def test_table_exposes_transparent_movement_metrics_not_combined_score():
    rows = build_ranking_movement_rows((
        obs("2026-08-20", 100),
        obs("2026-08-21", 80),
        obs("2026-08-22", 60),
        obs("2026-08-23", 35),
    ))
    table = ranking_movement_table_rows(rows)
    assert table[0]["Hisse"] == "AAA"
    assert "Sıçrama ivmesi" in table[0]
    assert "1S Δ" in table[0]
    assert "3S Δ" in table[0]
    assert "Top-5 uzaklık" in table[0]
    assert "Jump Score" not in table[0]


def test_morning_candidate_pool_uses_two_jump_slots_without_new_score():
    from dataclasses import dataclass
    from backend.app.analysis.morning_candidate_flow import build_morning_candidate_cards

    @dataclass
    class Signal:
        skor: int = 70
        karar: str = "Nötr Teknik Görünüm"
        pozitif_nedenler: tuple[str, ...] = ()
        riskler: tuple[str, ...] = ()

    @dataclass
    class Risk:
        risk_odul_orani: float = 1.5

    @dataclass
    class Candidate:
        sembol: str
        hacim_orani: float = 1.2
        sinyal: Signal = None
        risk_plani: Risk = None
        def __post_init__(self):
            self.sinyal = self.sinyal or Signal()
            self.risk_plani = self.risk_plani or Risk()

    @dataclass
    class Scan:
        adaylar: tuple[Candidate, ...]

    @dataclass
    class Visibility:
        symbol: str
        rank_change: int
        research_priority: str = "NORMAL"
        visibility_state: str = "IMPROVING"
        data_blocked: bool = False

    scan = Scan(tuple(Candidate(f"S{i}") for i in range(1, 11)))
    visibility = (
        Visibility("S8", 90),
        Visibility("S9", 80),
        Visibility("S10", 70),
    )
    cards = build_morning_candidate_cards(
        scan,
        visibility_contexts=visibility,
        limit=5,
        include_movement_pool=True,
    )
    assert [card.symbol for card in cards[:3]] == ["S1", "S2", "S3"]
    assert [card.symbol for card in cards[3:]] == ["S8", "S9"]
    assert [card.selection_source for card in cards] == ["TARAMA", "TARAMA", "TARAMA", "SICRAMA", "SICRAMA"]
