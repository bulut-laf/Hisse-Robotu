from backend.app.analysis.common_final_candidate_selection_v1 import (
    build_common_final_candidate_list,
)


def test_merges_same_symbol_across_sources_without_duplicate():
    result = build_common_final_candidate_list([
        {"symbol": " thyao ", "source": "TEKNIK_TARAMA", "horizon": "GUNLUK",
         "priority": 3, "technical_score": 72, "reason": "Teknik tarama"},
        {"symbol": "THYAO", "source": "FIRSAT_RADARI_HAFTALIK", "horizon": "HAFTALIK",
         "priority": 2, "technical_score": 75, "reason": "Haftalık radar"},
        {"symbol": "THYAO", "source": "SICRAMA", "horizon": "GUNLUK",
         "priority": 1, "entry_readiness": "GİRİŞE HAZIR", "reason": "Sıçrama"},
    ])
    assert len(result) == 1
    candidate = result[0]
    assert candidate.symbol == "THYAO"
    assert candidate.sources == ("TEKNIK_TARAMA", "FIRSAT_RADARI_HAFTALIK", "SICRAMA")
    assert candidate.horizons == ("GUNLUK", "HAFTALIK")
    assert candidate.technical_score == 75
    assert len(candidate.evidence) == 3
    assert len(candidate.reasons) == 3


def test_monthly_and_weekly_candidates_remain_distinguishable():
    result = build_common_final_candidate_list([
        {"symbol": "AAA", "source": "FIRSAT_RADARI_HAFTALIK", "horizon": "HAFTALIK"},
        {"symbol": "BBB", "source": "FIRSAT_RADARI_AYLIK", "horizon": "AYLIK"},
    ])
    by_symbol = {item.symbol: item for item in result}
    assert by_symbol["AAA"].horizons == ("HAFTALIK",)
    assert by_symbol["BBB"].horizons == ("AYLIK",)
    assert by_symbol["AAA"].sources != by_symbol["BBB"].sources


def test_blank_symbols_are_ignored_and_symbol_is_normalized():
    result = build_common_final_candidate_list([
        {"symbol": "", "source": "TEKNIK_TARAMA"},
        {"symbol": None, "source": "SICRAMA"},
        {"symbol": " akbnk ", "source": "TEKNIK_TARAMA"},
    ])
    assert [item.symbol for item in result] == ["AKBNK"]


def test_existing_priority_is_used_and_symbol_breaks_ties():
    result = build_common_final_candidate_list([
        {"symbol": "ZZZ", "source": "SICRAMA", "priority": 4},
        {"symbol": "BBB", "source": "TEKNIK_TARAMA", "priority": 2},
        {"symbol": "AAA", "source": "TEKNIK_TARAMA", "priority": 2},
    ])
    assert [item.symbol for item in result] == ["AAA", "BBB", "ZZZ"]


def test_limit_and_invalid_limit():
    rows = [
        {"symbol": "AAA", "source": "TEKNIK_TARAMA", "priority": 1},
        {"symbol": "BBB", "source": "TEKNIK_TARAMA", "priority": 2},
    ]
    assert len(build_common_final_candidate_list(rows, limit=1)) == 1
    assert build_common_final_candidate_list(rows, limit=0) == ()
    try:
        build_common_final_candidate_list(rows, limit=-1)
    except ValueError as exc:
        assert "limit" in str(exc)
    else:
        raise AssertionError("negative limit must raise ValueError")


def test_does_not_mutate_input_records():
    row = {"symbol": "ASELS", "source": "TEKNIK_TARAMA", "priority": 5}
    original = dict(row)
    build_common_final_candidate_list([row])
    assert row == original
