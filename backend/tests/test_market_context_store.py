\
import json

import pytest

from backend.app.market_context.models import MarketContextDocument
from backend.app.market_context.store import (
    DuplicateMarketContextError,
    MarketContextStore,
)


def _document(
    document_id="doc-001",
    raw_text="BIST100 güne pozitif başlayabilir.",
    source="ICBC",
):
    return MarketContextDocument(
        document_id=document_id,
        source=source,
        document_date="2026-08-03",
        imported_at="2026-08-03T07:00:00Z",
        input_type="text",
        raw_text=raw_text,
        content_hash="temporary",
    )


def test_ensure_directories_creates_storage_roots(tmp_path):
    store = MarketContextStore(tmp_path)

    store.ensure_directories()

    assert (tmp_path / "market_context_raw").is_dir()
    assert (tmp_path / "market_context_processed").is_dir()
    assert (tmp_path / "market_context_archive").is_dir()


def test_content_hash_is_stable_after_basic_normalization():
    first = MarketContextStore.content_hash(
        "BIST100   pozitif.\r\nDestek: 13200"
    )
    second = MarketContextStore.content_hash(
        "BIST100 pozitif.\nDestek: 13200"
    )

    assert first == second


def test_save_text_document_creates_raw_processed_and_manifest(tmp_path):
    store = MarketContextStore(tmp_path)

    saved = store.save_text_document(_document())

    raw = (
        tmp_path
        / "market_context_raw"
        / "2026-08-03"
        / "doc-001.txt"
    )
    processed = (
        tmp_path
        / "market_context_processed"
        / "2026-08-03"
        / "doc-001.json"
    )
    manifest = (
        tmp_path
        / "market_context_archive"
        / "2026-08-03"
        / "daily_manifest.json"
    )

    assert raw.exists()
    assert processed.exists()
    assert manifest.exists()
    assert saved.archive_status == "archived"
    assert saved.archive_date == "2026-08-03"

    payload = json.loads(processed.read_text(encoding="utf-8"))
    assert payload["document_id"] == "doc-001"
    assert payload["content_hash"] == saved.content_hash


def test_duplicate_content_is_rejected_even_with_different_document_id(tmp_path):
    store = MarketContextStore(tmp_path)

    store.save_text_document(_document(document_id="doc-001"))

    with pytest.raises(
        DuplicateMarketContextError,
        match="daha önce yüklenmiş",
    ):
        store.save_text_document(
            _document(document_id="doc-999")
        )


def test_same_day_multiple_distinct_reports_are_preserved(tmp_path):
    store = MarketContextStore(tmp_path)

    store.save_text_document(
        _document(
            document_id="doc-001",
            raw_text="ICBC piyasa bülteni.",
            source="ICBC",
        )
    )
    store.save_text_document(
        _document(
            document_id="doc-002",
            raw_text="Gedik piyasa bülteni.",
            source="Gedik",
        )
    )

    manifest = store.load_manifest("2026-08-03")

    assert manifest.document_count == 2
    assert set(manifest.sources) == {"ICBC", "Gedik"}
