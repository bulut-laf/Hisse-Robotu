from dataclasses import dataclass
from types import SimpleNamespace

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
    sinyal: Signal | None = None
    risk_plani: Risk | None = None

    def __post_init__(self):
        self.sinyal = self.sinyal or Signal()
        self.risk_plani = self.risk_plani or Risk()


@dataclass
class Visibility:
    symbol: str
    rank_change: int
    research_priority: str = "NORMAL"
    visibility_state: str = "IMPROVING"
    data_blocked: bool = False


def test_waiting_pool_preserves_three_scan_two_jump_contract():
    scan = SimpleNamespace(adaylar=tuple(Candidate(f"S{i}") for i in range(1, 11)))
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
    assert [card.symbol for card in cards] == ["S1", "S2", "S3", "S8", "S9"]
    assert [card.selection_source for card in cards] == [
        "TARAMA", "TARAMA", "TARAMA", "SICRAMA", "SICRAMA"
    ]
