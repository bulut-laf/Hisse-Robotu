from types import SimpleNamespace

from backend.app.analysis.eod_morning_board_delta import (
    build_eod_morning_board_delta,
    eod_morning_board_delta_rows,
)


def _candidate(symbol, rank, decision, readiness="TEYİT BEKLİYOR", source="TARAMA"):
    return SimpleNamespace(
        symbol=symbol,
        rank=rank,
        decision=decision,
        entry_readiness=readiness,
        jump_quality="UYGUN",
        selection_source=source,
    )


def _snapshot(*items):
    return SimpleNamespace(candidates=tuple(items))


def test_delta_summary_counts_decision_strengthening_and_weakening():
    evening = _snapshot(
        _candidate("AAA", 1, "BEKLE"),
        _candidate("BBB", 2, "AL", readiness="GİRİŞE HAZIR"),
        _candidate("CCC", 3, "İŞLEM YOK"),
    )
    morning = _snapshot(
        _candidate("AAA", 1, "AL", readiness="GİRİŞE HAZIR"),
        _candidate("BBB", 2, "BEKLE"),
        _candidate("CCC", 3, "İŞLEM YOK"),
    )
    summary = build_eod_morning_board_delta(evening, morning)
    assert summary is not None
    assert summary.evening_buy == 1
    assert summary.morning_buy == 1
    assert summary.upgrades == 1
    assert summary.downgrades == 1
    assert summary.unchanged == 1


def test_delta_summary_tracks_top5_membership_change():
    evening = _snapshot(
        _candidate("AAA", 1, "BEKLE"),
        _candidate("BBB", 2, "BEKLE"),
    )
    morning = _snapshot(
        _candidate("AAA", 1, "BEKLE"),
        _candidate("CCC", 2, "AL", readiness="GİRİŞE HAZIR", source="SICRAMA"),
    )
    summary = build_eod_morning_board_delta(evening, morning)
    assert summary is not None
    assert summary.added == 1
    assert summary.removed == 1
    rows = eod_morning_board_delta_rows(summary)
    assert {row["Değişim"] for row in rows} == {"YENİ", "ÇIKTI"}
    new_row = next(row for row in rows if row["Değişim"] == "YENİ")
    assert "SICRAMA" in new_row["Kısa neden"]


def test_delta_summary_returns_none_without_both_snapshots():
    assert build_eod_morning_board_delta(None, _snapshot()) is None
    assert build_eod_morning_board_delta(_snapshot(), None) is None


def test_dashboard_wires_single_look_delta_summary():
    with open("backend/dashboard.py", encoding="utf-8") as dosya:
        text = dosya.read()
    assert "Akşam → 09:00 Aksiyon Farkı — Tek Bakış" in text
    assert "build_eod_morning_board_delta" in text
    assert "eod_morning_board_delta_rows" in text
    assert "yeni skor, sinyal veya karar üretmez" in text
