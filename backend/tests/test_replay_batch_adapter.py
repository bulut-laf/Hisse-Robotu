from datetime import date

import pytest

from backend.app.history.replay_batch_adapter import (
    ReplayBatchAdapter,
    common_universe_mapper,
    rows_from_attribute,
    rows_from_mapping_result,
)


def test_common_universe_mapper():
    assert common_universe_mapper("BIST100") == "BIST 100"
    assert common_universe_mapper("BIST Tüm") == "BIST Tüm"


def test_adapter_runner_ve_extractor():
    calls = []

    def runner(*, cut_date, universe):
        calls.append((cut_date, universe))
        return [{"Hisse": "TRMET"}]

    adapter = ReplayBatchAdapter(
        runner=runner,
        rows_extractor=rows_from_mapping_result,
        universe_mapper=common_universe_mapper,
    )

    rows = adapter.scan_day(date(2026, 7, 1), "BIST100")
    assert rows == ({"Hisse": "TRMET"},)
    assert calls == [(date(2026, 7, 1), "BIST 100")]


def test_rows_from_attribute():
    class Result:
        export_rows = [{"Hisse": "AAA"}]

    extractor = rows_from_attribute("export_rows")
    assert extractor(Result()) == [{"Hisse": "AAA"}]


def test_rows_from_attribute_eksik():
    extractor = rows_from_attribute("missing")
    with pytest.raises(TypeError):
        extractor(object())


def test_rows_from_mapping_result_gecersiz():
    with pytest.raises(TypeError):
        rows_from_mapping_result("not rows")


def test_adapter_runner_callable_olmali():
    with pytest.raises(TypeError):
        ReplayBatchAdapter(runner=None, rows_extractor=rows_from_mapping_result)  # type: ignore[arg-type]


def test_attribute_name_bos_olamaz():
    with pytest.raises(ValueError):
        rows_from_attribute(" ")
