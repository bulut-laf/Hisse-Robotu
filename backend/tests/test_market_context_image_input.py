from datetime import datetime, timezone
import json

import pytest

from backend.app.market_context.image_input import (
    MarketContextImageArchive,
    MarketContextImageError,
    validate_market_context_image,
)


PNG = b"\x89PNG\r\n\x1a\n" + b"test-png"
JPEG = b"\xff\xd8\xff\xe0" + b"test-jpeg"


def test_png_girdisi_dogrulanir():
    image = validate_market_context_image(
        filename="WhatsApp Görsel 1.png",
        mime_type="image/png",
        data=PNG,
    )
    assert image.mime_type == "image/png"
    assert image.extension == ".png"
    assert image.safe_name.endswith(".png")
    assert image.sha256


def test_jpeg_jpg_ve_jpeg_desteklenir():
    first = validate_market_context_image(
        filename="mesaj.jpg",
        mime_type="image/jpeg",
        data=JPEG,
    )
    second = validate_market_context_image(
        filename="mesaj.jpeg",
        mime_type="image/jpeg",
        data=JPEG,
    )
    assert first.extension == ".jpg"
    assert second.extension == ".jpg"


def test_desteklenmeyen_mime_reddedilir():
    with pytest.raises(MarketContextImageError, match="JPG"):
        validate_market_context_image(
            filename="mesaj.webp",
            mime_type="image/webp",
            data=b"webp",
        )


def test_uzanti_mime_uyumsuzlugu_reddedilir():
    with pytest.raises(MarketContextImageError, match="uyumlu"):
        validate_market_context_image(
            filename="mesaj.png",
            mime_type="image/jpeg",
            data=JPEG,
        )


def test_sahte_png_imzasi_reddedilir():
    with pytest.raises(MarketContextImageError, match="imzası"):
        validate_market_context_image(
            filename="mesaj.png",
            mime_type="image/png",
            data=b"not-png",
        )


def test_boyut_siniri_uygulanir():
    with pytest.raises(MarketContextImageError, match="en fazla"):
        validate_market_context_image(
            filename="mesaj.jpg",
            mime_type="image/jpeg",
            data=JPEG + b"x" * 100,
            maximum_bytes=10,
        )


def test_orijinal_gorsel_ve_metadata_arsivlenir(tmp_path):
    image = validate_market_context_image(
        filename="WhatsApp mesajı.png",
        mime_type="image/png",
        data=PNG,
    )
    fixed = datetime(2026, 8, 5, 11, 30, tzinfo=timezone.utc)
    archive = MarketContextImageArchive(tmp_path, now_provider=lambda: fixed)
    item = archive.archive(image)

    assert item.file_path.read_bytes() == PNG
    assert item.file_path.parent.name == "2026-08-05"
    metadata = json.loads(item.metadata_path.read_text(encoding="utf-8"))
    assert metadata["sha256"] == image.sha256
    assert metadata["mime_type"] == "image/png"
    assert metadata["review"]["approved"] is False


def test_ayni_gorsel_tekrar_yuklenirse_mevcut_arsiv_kullanilir(tmp_path):
    image = validate_market_context_image(
        filename="mesaj.png",
        mime_type="image/png",
        data=PNG,
    )
    archive = MarketContextImageArchive(
        tmp_path,
        now_provider=lambda: datetime(2026, 8, 5, tzinfo=timezone.utc),
    )
    first = archive.archive(image)
    second = archive.archive(image)
    assert first.file_path == second.file_path
    assert first.reused_existing is False
    assert second.reused_existing is True


def test_kullanici_onayi_metadata_ile_kaydedilir(tmp_path):
    image = validate_market_context_image(
        filename="mesaj.jpg",
        mime_type="image/jpeg",
        data=JPEG,
    )
    archive = MarketContextImageArchive(
        tmp_path,
        now_provider=lambda: datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
    )
    item = archive.archive(image)
    archive.mark_review_approved(item, "TCMB açıklaması")
    metadata = json.loads(item.metadata_path.read_text(encoding="utf-8"))
    assert metadata["review"]["approved"] is True
    assert len(metadata["review"]["approved_text_sha256"]) == 64
