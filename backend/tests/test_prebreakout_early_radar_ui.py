from dataclasses import dataclass

import pytest

from backend.app.prebreakout.prebreakout_early_radar_ui import (
    EarlyRadarCard,
    as_row,
    card_from_output,
    compact_summary,
    render_early_radar_card,
    render_early_radar_panel,
    sort_cards,
    split_cards,
    status_level,
)


class FakeStreamlit:
    def __init__(self):
        self.calls = []

    def _add(self, name, *args):
        self.calls.append((name, args))

    def subheader(self, body): self._add("subheader", body)
    def caption(self, body): self._add("caption", body)
    def metric(self, label, value, delta=None): self._add("metric", label, value, delta)
    def info(self, body): self._add("info", body)
    def warning(self, body): self._add("warning", body)
    def success(self, body): self._add("success", body)
    def markdown(self, body): self._add("markdown", body)


@dataclass
class V:
    value: str


@dataclass
class FakeOutput:
    early_radar: object
    priority_score: float
    movement_phase: str
    maturity: object
    new_entry_message: str
    position_message: str
    reasons: tuple[str, ...]


def card(**kw):
    data = dict(
        symbol="TRMET",
        early_radar="Yüksek Öncelik",
        opportunity_score=72,
        movement_phase="ERKEN / GELİŞİYOR",
        maturity="Normal",
        new_entry_message="Erken Radar yüksek öncelik.",
        position_message="Trend korunuyor.",
        reasons=("Sıralama ivmesi yukarı.",),
    )
    data.update(kw)
    return EarlyRadarCard(**data)


def test_card_from_output():
    output = FakeOutput(
        early_radar=V("Yüksek Öncelik"),
        priority_score=74.5,
        movement_phase="ERKEN / GELİŞİYOR",
        maturity=V("Normal"),
        new_entry_message="İzle",
        position_message="Koru",
        reasons=("A", "B"),
    )
    result = card_from_output("trmet", output)
    assert result.symbol == "TRMET"
    assert result.early_radar == "Yüksek Öncelik"
    assert result.opportunity_score == pytest.approx(74.5)


def test_status_yuksek_oncelik_success():
    assert status_level(card()) == "success"


def test_status_izle_info():
    assert status_level(card(early_radar="İzle")) == "info"


def test_status_kar_koruma_warning():
    assert status_level(card(maturity="Kâr Koruma")) == "warning"


def test_status_yok_neutral():
    assert status_level(card(early_radar="Yok")) == "neutral"


def test_compact_summary():
    text = compact_summary(card())
    assert "TRMET" in text
    assert "72/100" in text


def test_as_row():
    row = as_row(card())
    assert row["Hisse"] == "TRMET"
    assert row["Erken Fırsat"] == 72.0
    assert "Yeni Giriş" in row


def test_sort_cards_firsat_puanina_gore():
    cards = [
        card(symbol="AAA", opportunity_score=50),
        card(symbol="BBB", opportunity_score=80),
    ]
    ordered = sort_cards(cards)
    assert [x.symbol for x in ordered] == ["BBB", "AAA"]


def test_sort_cards_kar_korumayi_erken_listeden_sona_iter():
    cards = [
        card(symbol="AAA", opportunity_score=90, maturity="Kâr Koruma"),
        card(symbol="BBB", opportunity_score=70),
    ]
    ordered = sort_cards(cards)
    assert [x.symbol for x in ordered] == ["BBB", "AAA"]


def test_split_cards():
    cards = [
        card(symbol="AAA", early_radar="Yüksek Öncelik"),
        card(symbol="BBB", maturity="Kâr Koruma", early_radar="Yok"),
        card(symbol="CCC", early_radar="Yok"),
    ]
    early, maturity = split_cards(cards)
    assert [x.symbol for x in early] == ["AAA"]
    assert [x.symbol for x in maturity] == ["BBB"]


def test_render_success_card():
    st = FakeStreamlit()
    render_early_radar_card(st, card())
    names = [x[0] for x in st.calls]
    assert "success" in names
    assert "metric" in names
    assert "warning" not in names


def test_render_warning_card():
    st = FakeStreamlit()
    render_early_radar_card(
        st,
        card(
            maturity="Kâr Koruma",
            early_radar="Yok",
            movement_phase="OLGUN",
        ),
    )
    names = [x[0] for x in st.calls]
    assert names.count("warning") == 2


def test_render_panel_bos_listeler():
    st = FakeStreamlit()
    render_early_radar_panel(st, [])
    info_texts = [args[0] for name, args in st.calls if name == "info"]
    assert "Şu anda Erken Radar adayı yok." in info_texts
    assert "Şu anda Kâr Koruma uyarısı yok." in info_texts


def test_render_panel_iki_bolum():
    st = FakeStreamlit()
    render_early_radar_panel(
        st,
        [
            card(symbol="AAA"),
            card(symbol="BBB", early_radar="Yok", maturity="Kâr Koruma"),
        ],
    )
    headers = [args[0] for name, args in st.calls if name == "subheader"]
    assert "Erken Radar" in headers
    assert "Olgunlaşma / Kâr Koruma" in headers
    assert "AAA" in headers
    assert "BBB" in headers


def test_gecersiz_puan_reddedilir():
    with pytest.raises(ValueError):
        card(opportunity_score=101)


def test_bos_symbol_reddedilir():
    with pytest.raises(ValueError):
        card(symbol=" ")
