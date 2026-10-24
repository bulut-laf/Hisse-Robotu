\
from backend.app.market_context.archive import (
    DailyArchiveDocumentRef,
    DailyArchiveManifest,
)


def _ref(
    document_id="doc-001",
    content_hash="hash-001",
    source="ICBC",
):
    return DailyArchiveDocumentRef(
        document_id=document_id,
        source=source,
        document_date="2026-08-03",
        input_type="text",
        content_hash=content_hash,
        raw_path="market_context_raw/2026-08-03/doc-001.txt",
        processed_path="market_context_processed/2026-08-03/doc-001.json",
    )


def test_daily_manifest_accepts_multiple_reports():
    manifest = DailyArchiveManifest(date="2026-08-03")

    assert manifest.add_document(_ref()) is True
    assert manifest.add_document(
        _ref(
            document_id="doc-002",
            content_hash="hash-002",
            source="Gedik",
        )
    ) is True

    assert manifest.document_count == 2
    assert manifest.sources == ["Gedik", "ICBC"]


def test_daily_manifest_rejects_same_content_hash():
    manifest = DailyArchiveManifest(date="2026-08-03")

    assert manifest.add_document(_ref()) is True
    assert manifest.add_document(
        _ref(
            document_id="doc-999",
            content_hash="hash-001",
            source="Başka Kaynak",
        )
    ) is False

    assert manifest.document_count == 1


def test_manifest_round_trip_to_disk(tmp_path):
    manifest = DailyArchiveManifest(
        date="2026-08-03",
        created_at="2026-08-03T07:00:00Z",
        updated_at="2026-08-03T07:10:00Z",
    )
    manifest.add_document(_ref())

    path = tmp_path / "2026-08-03" / "daily_manifest.json"
    manifest.save(path)

    restored = DailyArchiveManifest.load(path)

    assert restored.date == "2026-08-03"
    assert restored.document_count == 1
    assert restored.documents[0].document_id == "doc-001"
    assert restored.ai_review_status == "not_reviewed"


def test_ai_fields_exist_but_do_not_generate_ai_review():
    manifest = DailyArchiveManifest(date="2026-08-03")

    assert manifest.ai_review_status == "not_reviewed"
    assert manifest.ai_review_id is None
