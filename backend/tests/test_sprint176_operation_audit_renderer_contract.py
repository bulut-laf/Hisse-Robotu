from pathlib import Path


RENDERER = Path("backend/app/ui/official_source_feed_renderer.py")


def source():
    return RENDERER.read_text(encoding="utf-8")


def test_operation_store_renderer_importunda():
    text = source()
    assert "OfficialSourceOperationStore" in text
    assert "OfficialSourceOperationKind" in text


def test_preview_blocked_kaydedilir():
    text = source()
    assert "OfficialSourceOperationKind.PREVIEW_BLOCKED" in text


def test_preview_success_kaydedilir():
    assert "OfficialSourceOperationKind.PREVIEW_SUCCESS" in source()


def test_preview_error_kaydedilir():
    assert "OfficialSourceOperationKind.PREVIEW_ERROR" in source()


def test_archive_success_kaydedilir():
    assert "OfficialSourceOperationKind.ARCHIVE_SUCCESS" in source()


def test_archive_duplicate_kaydedilir():
    assert "OfficialSourceOperationKind.ARCHIVE_DUPLICATE" in source()


def test_archive_error_kaydedilir():
    assert "OfficialSourceOperationKind.ARCHIVE_ERROR" in source()


def test_audit_hatasi_ana_akisi_durdurmaz():
    text = source()
    assert 'st.caption(f"Operasyon günlüğü yazılamadı: {exc}")' in text


def test_renderer_default_store_yaratir():
    text = source()
    assert "store = operation_store or OfficialSourceOperationStore()" in text


def test_ag_onayi_kapaliyken_adapter_fetch_once_bile_cagrilmaz():
    text = source()
    blocked_pos = text.index("OfficialSourceOperationKind.PREVIEW_BLOCKED")
    fetch_pos = text.index("spec.adapter_type(network_enabled=True).fetch(source_url)")
    assert blocked_pos < fetch_pos


def test_haber_body_operasyon_loguna_verilmez():
    text = source()
    assert "detail=preview_item.body" not in text
    assert "detail=result.item.body" not in text
    assert "source_reference=preview_item.body" not in text
    assert "source_reference=result.item.body" not in text


def test_eski_guvenlik_akisi_korunur():
    text = source()
    assert "value=False" in text
    assert "disabled=preview.duplicate" in text
    assert "FeedIngestionService(archive).preview(result.item)" in text
    assert "FeedIngestionService(archive).import_item(preview_item)" in text
