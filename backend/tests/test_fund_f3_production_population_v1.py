from datetime import datetime, timezone

import backend.app.funds.f3_production_population as runtime
import backend.app.funds.tefas_history_population as history_population

from backend.app.funds.store import (
    FundObservationJsonStore,
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


def universe_row(code):
    return {
        "fonkod": code,
    }


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


def persist_complete_history(
    store,
    code,
):
    observations = (
        history_rows_to_observations(
            (
                history_row(
                    code,
                    "2026-08-01",
                    "100",
                ),
                history_row(
                    code,
                    "2026-08-02",
                    "101",
                ),
                history_row(
                    code,
                    "2026-08-03",
                    "102",
                ),
            ),
            fund_code=code,
            fetched_at=STAMP,
            source_as_of=STAMP,
        )
    )

    store.upsert(
        observations
    )


def test_selection_is_sorted_bounded_and_resumable(
    tmp_path,
):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    persist_complete_history(
        store,
        "BBB",
    )

    selected = runtime.select_next_f3_batch(
        (
            universe_row("CCC"),
            universe_row("BBB"),
            universe_row("AAA"),
        ),
        store=store,
        batch_size=2,
    )

    assert selected == (
        "AAA",
        "CCC",
    )


def test_invalid_batch_size_is_blocked(
    tmp_path,
):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    import pytest

    with pytest.raises(
        ValueError,
        match="BATCH_SIZE_INVALID",
    ):
        runtime.select_next_f3_batch(
            (universe_row("AAA"),),
            store=store,
            batch_size=51,
        )


def test_individual_failure_does_not_destroy_progress(
    tmp_path,
    monkeypatch,
):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    monkeypatch.setattr(
        runtime,
        "fetch_tefas_universe_rows",
        lambda: (
            universe_row("AAA"),
            universe_row("BBB"),
            universe_row("CCC"),
        ),
    )

    def fake_history_fetch(
        fund_code,
        *,
        period=1,
        timeout_seconds=10,
    ):
        if fund_code == "BBB":
            raise RuntimeError(
                "TEST_PROVIDER_FAILURE"
            )

        return (
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
        )

    monkeypatch.setattr(
        history_population,
        "fetch_tefas_fund_history_rows",
        fake_history_fetch,
    )

    result = (
        runtime
        .populate_next_f3_production_batch(
            batch_size=3,
            store=store,
        )
    )

    assert result.status == "PARTIAL"

    assert result.succeeded_funds == (
        "AAA",
        "CCC",
    )

    assert len(
        result.failed_funds
    ) == 1

    assert result.failed_funds[
        0
    ].startswith(
        "BBB:"
    )

    completed = runtime.completed_f3_codes(
        store
    )

    assert completed == frozenset(
        {
            "AAA",
            "CCC",
        }
    )


def test_second_run_skips_completed_funds(
    tmp_path,
):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    persist_complete_history(
        store,
        "AAA",
    )

    selected = runtime.select_next_f3_batch(
        (
            universe_row("AAA"),
            universe_row("BBB"),
        ),
        store=store,
        batch_size=50,
    )

    assert selected == (
        "BBB",
    )
