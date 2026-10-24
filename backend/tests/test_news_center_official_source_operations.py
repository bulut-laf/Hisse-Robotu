from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from backend.app.news_center.official_source_operations import (
    OfficialSourceOperationError,
    OfficialSourceOperationKind,
    OfficialSourceOperationStore,
    sanitize_source_reference,
    summarize_official_source_operations,
)


def test_sanitize_query_fragment_ve_userinfo_siler():
    value = sanitize_source_reference(
        "https://user:secret@www.kap.org.tr/tr/Bildirim/123?token=abc#frag"
    )
    assert value == "https://www.kap.org.tr/tr/Bildirim/123"
    assert "secret" not in value
    assert "token" not in value


@pytest.mark.parametrize(
    "value",
    (
        "",
        "not a url",
        "javascript:alert(1)",
        "https://",
        "https://host:bad/path",
    ),
)
def test_sanitize_gecersiz_url_ham_gizli_metin_saklamaz(value):
    result = sanitize_source_reference(value)
    if not value:
        assert result == ""
    else:
        assert result == "[geçersiz-url]"


def test_append_ve_read_roundtrip(tmp_path: Path):
    store = OfficialSourceOperationStore(tmp_path / "ops.jsonl")
    at = datetime(2026, 8, 5, 20, 0, tzinfo=timezone.utc)

    saved = store.append(
        "KAP",
        OfficialSourceOperationKind.PREVIEW_SUCCESS,
        source_reference="https://www.kap.org.tr/tr/Bildirim/1?x=y",
        detail="başarılı\nönizleme",
        occurred_at=at,
    )
    result = store.read()

    assert result.invalid_lines == 0
    assert result.records == (saved,)
    assert saved.source_reference == "https://www.kap.org.tr/tr/Bildirim/1"
    assert saved.detail == "başarılı önizleme"
    assert saved.occurred_at == at


def test_tier1_olmayan_kaynak_reddedilir(tmp_path: Path):
    store = OfficialSourceOperationStore(tmp_path / "ops.jsonl")
    with pytest.raises(OfficialSourceOperationError, match="Tier-1"):
        store.append(
            "Bilinmeyen Kaynak",
            OfficialSourceOperationKind.PREVIEW_SUCCESS,
        )


def test_yeni_kayitlar_once_doner(tmp_path: Path):
    store = OfficialSourceOperationStore(tmp_path / "ops.jsonl")
    base = datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc)
    store.append(
        "KAP",
        OfficialSourceOperationKind.PREVIEW_SUCCESS,
        occurred_at=base,
    )
    store.append(
        "TCMB",
        OfficialSourceOperationKind.PREVIEW_ERROR,
        occurred_at=base + timedelta(minutes=1),
    )

    records = store.read().records
    assert [item.source_name for item in records] == ["TCMB", "KAP"]


def test_source_filter(tmp_path: Path):
    store = OfficialSourceOperationStore(tmp_path / "ops.jsonl")
    store.append("KAP", OfficialSourceOperationKind.PREVIEW_SUCCESS)
    store.append("TCMB", OfficialSourceOperationKind.PREVIEW_SUCCESS)

    result = store.read(source_name="KAP")
    assert len(result.records) == 1
    assert result.records[0].source_name == "KAP"


def test_kind_filter(tmp_path: Path):
    store = OfficialSourceOperationStore(tmp_path / "ops.jsonl")
    store.append("KAP", OfficialSourceOperationKind.PREVIEW_SUCCESS)
    store.append("KAP", OfficialSourceOperationKind.ARCHIVE_SUCCESS)

    result = store.read(
        kinds=(OfficialSourceOperationKind.ARCHIVE_SUCCESS,)
    )
    assert len(result.records) == 1
    assert result.records[0].kind is OfficialSourceOperationKind.ARCHIVE_SUCCESS


@pytest.mark.parametrize("limit", (0, 5001))
def test_limit_siniri(limit, tmp_path: Path):
    store = OfficialSourceOperationStore(tmp_path / "ops.jsonl")
    with pytest.raises(ValueError, match="limit"):
        store.read(limit=limit)


def test_olmayan_dosya_bos_sonuc(tmp_path: Path):
    result = OfficialSourceOperationStore(
        tmp_path / "missing.jsonl"
    ).read()
    assert result.records == ()
    assert result.invalid_lines == 0


def test_bozuk_satir_atlanir_ve_sayilir(tmp_path: Path):
    path = tmp_path / "ops.jsonl"
    store = OfficialSourceOperationStore(path)
    store.append("KAP", OfficialSourceOperationKind.PREVIEW_SUCCESS)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{bozuk json}\n")

    result = store.read()
    assert len(result.records) == 1
    assert result.invalid_lines == 1


def test_haber_govdesi_gibi_buyuk_detail_kirpilir(tmp_path: Path):
    store = OfficialSourceOperationStore(tmp_path / "ops.jsonl")
    record = store.append(
        "KAP",
        OfficialSourceOperationKind.PREVIEW_ERROR,
        detail="X" * 2000,
    )
    assert len(record.detail) == 500


def test_summarize_preview_archive_success(tmp_path: Path):
    store = OfficialSourceOperationStore(tmp_path / "ops.jsonl")
    base = datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc)

    store.append(
        "KAP",
        OfficialSourceOperationKind.PREVIEW_SUCCESS,
        occurred_at=base,
    )
    store.append(
        "KAP",
        OfficialSourceOperationKind.ARCHIVE_SUCCESS,
        occurred_at=base + timedelta(minutes=1),
    )

    summary = summarize_official_source_operations(
        store.read().records,
        ("KAP",),
    )[0]

    assert summary.last_preview_kind is OfficialSourceOperationKind.PREVIEW_SUCCESS
    assert summary.last_archive_kind is OfficialSourceOperationKind.ARCHIVE_SUCCESS
    assert summary.last_success_at == base + timedelta(minutes=1)


def test_summarize_error_basari_zamanini_bozmaz(tmp_path: Path):
    store = OfficialSourceOperationStore(tmp_path / "ops.jsonl")
    base = datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc)

    store.append(
        "KAP",
        OfficialSourceOperationKind.PREVIEW_SUCCESS,
        occurred_at=base,
    )
    store.append(
        "KAP",
        OfficialSourceOperationKind.PREVIEW_ERROR,
        occurred_at=base + timedelta(minutes=2),
    )

    summary = summarize_official_source_operations(
        store.read().records,
        ("KAP",),
    )[0]

    assert summary.last_preview_kind is OfficialSourceOperationKind.PREVIEW_ERROR
    assert summary.last_success_at == base


def test_summarize_blocked_preview_basari_sayilmaz(tmp_path: Path):
    store = OfficialSourceOperationStore(tmp_path / "ops.jsonl")
    at = datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc)
    store.append(
        "TCMB",
        OfficialSourceOperationKind.PREVIEW_BLOCKED,
        occurred_at=at,
    )

    summary = summarize_official_source_operations(
        store.read().records,
        ("TCMB",),
    )[0]

    assert summary.last_preview_kind is OfficialSourceOperationKind.PREVIEW_BLOCKED
    assert summary.last_success_at is None


def test_summarize_kaynak_sirasini_korur():
    summaries = summarize_official_source_operations(
        (),
        ("KAP", "TCMB", "TÜİK"),
    )
    assert [item.source_name for item in summaries] == ["KAP", "TCMB", "TÜİK"]


def test_jsonl_haber_body_alani_tasimaz(tmp_path: Path):
    path = tmp_path / "ops.jsonl"
    store = OfficialSourceOperationStore(path)
    store.append(
        "KAP",
        OfficialSourceOperationKind.ARCHIVE_SUCCESS,
        detail="kısa sonuç",
    )
    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert "body" not in payload
    assert set(payload) == {
        "operation_id",
        "source_name",
        "kind",
        "occurred_at",
        "source_reference",
        "detail",
    }
