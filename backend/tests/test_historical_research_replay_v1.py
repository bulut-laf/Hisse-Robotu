from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace

import pytest

import backend.app.analysis.historical_research_replay as replay
from backend.app.data.batch_market_data import BatchMarketDataResult


def test_cut_date_fetcher_forwards_upper_date_and_disables_latest_official_merge():
    calls = []

    def fetcher(
        symbols,
        *,
        islem_gunu=160,
        indirme_donemi="1y",
        bugun=None,
        resmi_veriyi_birlestir=None,
    ):
        calls.append(
            {
                "symbols": tuple(symbols),
                "bugun": bugun,
                "resmi_veriyi_birlestir": resmi_veriyi_birlestir,
            }
        )
        return BatchMarketDataResult(veriler={}, hatalar=())

    cut = date(2026, 8, 21)
    bound = replay.build_cut_date_fetcher(cut, base_fetcher=fetcher)
    bound(("AAA.IS",), islem_gunu=160, indirme_donemi="1y")

    assert calls == [
        {
            "symbols": ("AAA.IS",),
            "bugun": cut,
            "resmi_veriyi_birlestir": False,
        }
    ]


def test_cut_date_fetcher_fails_closed_without_explicit_date_seam():
    def unsafe_fetcher(symbols, *, islem_gunu=160, indirme_donemi="1y"):
        return BatchMarketDataResult(veriler={}, hatalar=())

    with pytest.raises(ValueError, match="bugun"):
        replay.build_cut_date_fetcher(
            date(2026, 8, 21),
            base_fetcher=unsafe_fetcher,
        )


def test_replay_uses_full_filtered_research_rows_and_never_persists(monkeypatch):
    cut = date(2026, 8, 21)
    fetch_calls = []

    def fetcher(
        symbols,
        *,
        islem_gunu=160,
        indirme_donemi="1y",
        bugun=None,
    ):
        fetch_calls.append((tuple(symbols), bugun))
        return BatchMarketDataResult(veriler={}, hatalar=())

    candidates = tuple(
        SimpleNamespace(
            sembol=f"S{i:03d}.IS",
            analiz_tarihi=cut.isoformat(),
            sinyal=SimpleNamespace(skor=float(200 - i)),
        )
        for i in range(1, 121)
    )

    fake_scan = SimpleNamespace(
        basarili_sonuclar=candidates,
        hatalar=(),
    )

    class FakeScanner:
        def __init__(self, *, veri_getirici):
            self._fetch = veri_getirici

        def tara(self, symbols):
            self._fetch(
                symbols,
                islem_gunu=160,
                indirme_donemi="1y",
            )
            return fake_scan

    monkeypatch.setattr(replay, "BatchStockScanner", FakeScanner)
    monkeypatch.setattr(
        replay,
        "profil_al",
        lambda _name: SimpleNamespace(kriterler=object()),
    )
    monkeypatch.setattr(
        replay,
        "tarama_sonucunu_filtrele",
        lambda *, tarama, kriterler: SimpleNamespace(adaylar=candidates),
    )

    result = replay.replay_canonical_research(
        as_of=cut,
        symbols=("AAA", "BBB"),
        profile_name="dengeli",
        universe_source="TEST_HISTORICAL_XUTUM",
        base_fetcher=fetcher,
    )

    assert fetch_calls == [(("AAA.IS", "BBB.IS"), cut)]
    assert result.ranked_research_count == 120
    assert len(result.rows) == 120
    assert result.rows[0]["Sıra"] == 1
    assert result.rows[-1]["Sıra"] == 120
    assert len(result.observations) == 120

    # Adapter does not receive or construct RankObservationJsonlStore;
    # persistence is intentionally outside this capability.
    assert "RankObservationJsonlStore" not in replay.__dict__


def test_replay_fails_closed_on_future_analysis_date(monkeypatch):
    cut = date(2026, 8, 21)

    def fetcher(
        symbols,
        *,
        islem_gunu=160,
        indirme_donemi="1y",
        bugun=None,
    ):
        return BatchMarketDataResult(veriler={}, hatalar=())

    future_candidate = SimpleNamespace(
        sembol="AAA.IS",
        analiz_tarihi="2026-08-24",
        sinyal=SimpleNamespace(skor=90.0),
    )

    fake_scan = SimpleNamespace(
        basarili_sonuclar=(future_candidate,),
        hatalar=(),
    )

    class FakeScanner:
        def __init__(self, *, veri_getirici):
            self._fetch = veri_getirici

        def tara(self, symbols):
            self._fetch(symbols, islem_gunu=160, indirme_donemi="1y")
            return fake_scan

    monkeypatch.setattr(replay, "BatchStockScanner", FakeScanner)
    monkeypatch.setattr(
        replay,
        "profil_al",
        lambda _name: SimpleNamespace(kriterler=object()),
    )
    monkeypatch.setattr(
        replay,
        "tarama_sonucunu_filtrele",
        lambda *, tarama, kriterler: SimpleNamespace(
            adaylar=(future_candidate,)
        ),
    )

    with pytest.raises(ValueError, match="future leakage"):
        replay.replay_canonical_research(
            as_of=cut,
            symbols=("AAA",),
            base_fetcher=fetcher,
        )


def test_contract_phrase_is_preserved():
    source = replay.__doc__ or ""
    assert "yeni teknik skor, işlem sinyali veya AL/SAT kararı üretmez" in source