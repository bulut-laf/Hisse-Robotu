from datetime import datetime, timezone

from backend.app.funds.evidence_mapper import EvidenceState
from backend.app.funds.f3_store_read_model import (
    analyze_tefas_rows_with_f3_store,
    enrich_evidence_maps_with_f3_store,
    price_histories_from_store,
)
from backend.app.funds.live_pipeline import (
    evidence_from_tefas_rows,
)
from backend.app.funds.store import FundObservationJsonStore
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
    code: str,
    day: str,
    price: object,
) -> dict[str, object]:
    return {
        "fonKodu": code,
        "fonUnvan": "TEST",
        "kategoriDerece": 0,
        "kategoriFonSay": 29,
        "tarih": day,
        "fiyat": price,
    }


def universe_row(
    code: str,
) -> dict[str, object]:
    return {
        "fonkod": code,
        "getiri1a": "1,00",
        "getiri3a": "3,00",
        "getiri6a": "5,00",
    }


def write_history(
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

    return store.upsert(
        observations
    )


def test_store_records_rebuild_price_history_in_date_order(
    tmp_path,
):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    write_history(
        store,
        "AAA",
        (
            "100",
            "101",
            "102",
            "103",
        ),
    )

    histories = price_histories_from_store(
        store,
        canonical_fund_ids=(
            "fund:tefas:AAA",
        ),
    )

    assert tuple(
        str(value)
        for value in histories[
            "fund:tefas:AAA"
        ]
    ) == (
        "100",
        "101",
        "102",
        "103",
    )


def test_store_f3_replaces_only_f3_family(
    tmp_path,
):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    write_history(
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

    write_history(
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

    base = evidence_from_tefas_rows(
        (
            universe_row("AAA"),
            universe_row("BBB"),
        )
    )

    enriched = enrich_evidence_maps_with_f3_store(
        base,
        store=store,
    )

    by_id = {
        item.canonical_fund_id: item
        for item in enriched
    }

    aaa = by_id["fund:tefas:AAA"]
    bbb = by_id["fund:tefas:BBB"]

    aaa_f3 = next(
        x for x in aaa.evidence
        if x.family == "F3"
    )

    bbb_f3 = next(
        x for x in bbb.evidence
        if x.family == "F3"
    )

    assert aaa_f3.state is EvidenceState.POSITIVE
    assert bbb_f3.state is EvidenceState.CAUTION

    # Existing F2 remains present.
    assert next(
        x for x in aaa.evidence
        if x.family == "F2"
    ).state is not EvidenceState.UNAVAILABLE


def test_missing_store_history_preserves_f3_unavailable(
    tmp_path,
):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    base = evidence_from_tefas_rows(
        (
            universe_row("AAA"),
        )
    )

    enriched = enrich_evidence_maps_with_f3_store(
        base,
        store=store,
    )

    f3 = next(
        x
        for x in enriched[0].evidence
        if x.family == "F3"
    )

    assert f3.state is EvidenceState.UNAVAILABLE


def test_store_backed_analysis_reuses_existing_analysis_engine(
    tmp_path,
):
    store = FundObservationJsonStore(
        tmp_path / "observations.json"
    )

    write_history(
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

    write_history(
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

    results = analyze_tefas_rows_with_f3_store(
        (
            universe_row("AAA"),
            universe_row("BBB"),
        ),
        store=store,
    )

    by_id = {
        item.canonical_fund_id: item
        for item in results
    }

    assert "F3" in (
        by_id["fund:tefas:AAA"].positive_families
    )

    assert "F3" in (
        by_id["fund:tefas:BBB"].caution_families
    )

    assert all(
        item.automatic_trade_authority == "NONE"
        for item in results
    )

    assert all(
        item.forced_fill is False
        for item in results
    )
