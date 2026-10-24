from datetime import datetime, timezone
from pathlib import Path

import backend.app.funds.live_pipeline as live
import backend.app.funds.store as store_module
import backend.app.funds.tefas_adapter as adapter
import backend.app.funds.tefas_history_population as population

from backend.app.funds.store import (
    FundObservationJsonStore,
    fund_observation_store,
)
from backend.app.funds.tefas_history_population import (
    history_rows_to_observations,
)


STAMP = datetime(
    2026,
    9,
    2,
    12,
    0,
    tzinfo=timezone.utc,
)


def history_row(
    code,
    day,
    price,
):
    return {
        "fonKodu": code,
        "fonUnvan": "TEST",
        "kategoriDerece": 0,
        "kategoriFonSay": 29,
        "tarih": day,
        "fiyat": price,
    }


def universe_row(
    code,
):
    return {
        "fonkod": code,
        "getiri1a": "1,00",
        "getiri3a": "3,00",
        "getiri6a": "5,00",
    }


def persist_history(
    store,
    code,
    prices,
):
    rows = tuple(
        history_row(
            code,
            f"2026-08-{index:02d}",
            price,
        )
        for index, price
        in enumerate(
            prices,
            start=1,
        )
    )

    observations = history_rows_to_observations(
        rows,
        fund_code=code,
        fetched_at=STAMP,
        source_as_of=STAMP,
    )

    store.upsert(
        observations
    )


def test_default_store_path_is_canonical():
    path = (
        store_module
        .DEFAULT_FUND_OBSERVATION_PATH
        .as_posix()
    )

    assert path.endswith(
        "/backend/data/funds/observations.json"
    )


def test_factory_uses_default_store_path():
    result = fund_observation_store()

    assert isinstance(
        result,
        FundObservationJsonStore,
    )

    assert (
        result.path
        == store_module.DEFAULT_FUND_OBSERVATION_PATH
    )


def test_live_runtime_reads_f3_from_store_without_history_network(
    tmp_path,
    monkeypatch,
):
    store_path = (
        tmp_path
        / "funds"
        / "observations.json"
    )

    monkeypatch.setattr(
        store_module,
        "DEFAULT_FUND_OBSERVATION_PATH",
        store_path,
    )

    store = fund_observation_store()

    persist_history(
        store,
        "AAA",
        (
            "100",
            "101",
            "102",
            "103",
            "104",
        ),
    )

    persist_history(
        store,
        "BBB",
        (
            "100",
            "120",
            "80",
            "130",
            "70",
        ),
    )

    monkeypatch.setattr(
        live,
        "fetch_tefas_universe_rows",
        lambda: (
            universe_row("AAA"),
            universe_row("BBB"),
        ),
    )

    def history_network_forbidden(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "HISTORY_NETWORK_CALLED_FROM_UI_RUNTIME"
        )

    monkeypatch.setattr(
        adapter,
        "fetch_tefas_fund_history_rows",
        history_network_forbidden,
    )

    results = live.run_live_fund_analysis()

    assert len(results) == 2

    by_id = {
        item.canonical_fund_id: item
        for item in results
    }

    assert "F3" in (
        by_id[
            "fund:tefas:AAA"
        ].positive_families
    )

    assert "F3" in (
        by_id[
            "fund:tefas:BBB"
        ].caution_families
    )

    assert all(
        item.automatic_trade_authority
        == "NONE"
        for item in results
    )

    assert all(
        item.forced_fill is False
        for item in results
    )


def test_missing_production_store_keeps_f3_unavailable(
    tmp_path,
    monkeypatch,
):
    missing = (
        tmp_path
        / "does-not-exist"
        / "observations.json"
    )

    monkeypatch.setattr(
        store_module,
        "DEFAULT_FUND_OBSERVATION_PATH",
        missing,
    )

    monkeypatch.setattr(
        live,
        "fetch_tefas_universe_rows",
        lambda: (
            universe_row("AAA"),
        ),
    )

    results = live.run_live_fund_analysis()

    assert len(results) == 1

    assert (
        "F3"
        in results[0].unavailable_families
    )

    # Read-only execution must not create the store.
    assert not missing.exists()


def test_default_population_entrypoint_uses_existing_store_factory(
    tmp_path,
    monkeypatch,
):
    target = (
        tmp_path
        / "observations.json"
    )

    store = FundObservationJsonStore(
        target
    )

    monkeypatch.setattr(
        population,
        "fund_observation_store",
        lambda: store,
    )

    monkeypatch.setattr(
        population,
        "fetch_tefas_fund_history_rows",
        lambda fund_code, **kwargs: (
            history_row(
                fund_code,
                "2026-08-01",
                "100",
            ),
            history_row(
                fund_code,
                "2026-08-02",
                "101",
            ),
            history_row(
                fund_code,
                "2026-08-03",
                "102",
            ),
        ),
    )

    result = (
        population
        .populate_default_tefas_history_batch(
            ("AAA",),
            maximum_funds=1,
            fetched_at=STAMP,
            source_as_of=STAMP,
        )
    )

    assert result.fetched_funds == 1
    assert result.observation_count == 3
    assert target.exists()
