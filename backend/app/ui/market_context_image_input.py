from __future__ import annotations

from pathlib import Path

from backend.app.market_context.image_input import (
    GeminiMarketContextImageExtractor,
    MarketContextImageArchive,
    MarketContextImageError,
    MarketContextImageExtractionError,
    validate_market_context_image,
)


IMAGE_UPLOAD_GENERATION_KEY = "market_context_image_upload_generation"
IMAGE_CURRENT_DIGEST_KEY = "market_context_image_current_digest"
IMAGE_APPROVED_TEXT_KEY = "market_context_image_approved_text"
IMAGE_APPROVED_DIGEST_KEY = "market_context_image_approved_digest"
IMAGE_TRANSFER_TOKEN_KEY = "market_context_image_last_transfer_token"


def _session_key(prefix: str, digest: str) -> str:
    return f"market_context_image_{prefix}_{digest[:20]}"


def _upload_widget_key(st) -> str:
    try:
        generation = int(st.session_state.get(IMAGE_UPLOAD_GENERATION_KEY, 0) or 0)
    except (TypeError, ValueError):
        generation = 0
    return f"market_context_image_upload_{max(generation, 0)}"


def render_market_context_image_input(st, *, project_root: Path) -> str:
    """JPG/PNG ekran görüntüsünü arşivler ve onaylanmış metni döndürür.

    Bu yardımcı teknik skor, işlem kararı veya piyasa sınıflandırması üretmez.
    Metin ancak kullanıcı kontrol edip onayladığında mevcut Seans Öncesi Bağlam
    kayıt akışına döner.
    """

    st.caption(
        "WhatsApp veya benzeri ekran görüntülerini JPG/JPEG/PNG olarak yükleyin. "
        "Telefon numarası, isim veya başka kişisel bilgiler varsa mümkünse yüklemeden "
        "önce kırpın. Görselin orijinali ayrı arşivde saklanır."
    )
    uploaded = st.file_uploader(
        "Ekran görüntüsü",
        type=("jpg", "jpeg", "png"),
        accept_multiple_files=False,
        key=_upload_widget_key(st),
    )
    if uploaded is None:
        return ""

    try:
        image = validate_market_context_image(
            filename=getattr(uploaded, "name", "gorsel"),
            mime_type=getattr(uploaded, "type", ""),
            data=uploaded.getvalue(),
        )
    except (MarketContextImageError, OSError, ValueError, TypeError) as exc:
        st.error(str(exc))
        return ""

    previous_digest = str(st.session_state.get(IMAGE_CURRENT_DIGEST_KEY, "") or "")
    if previous_digest != image.sha256:
        st.session_state[IMAGE_CURRENT_DIGEST_KEY] = image.sha256
        st.session_state.pop(IMAGE_APPROVED_TEXT_KEY, None)
        st.session_state.pop(IMAGE_APPROVED_DIGEST_KEY, None)
        st.session_state.pop(IMAGE_TRANSFER_TOKEN_KEY, None)

    st.image(image.data, caption=image.original_name, width="stretch")

    archive = MarketContextImageArchive(
        Path(project_root) / "backend" / "data" / "market_context_image_archive"
    )
    try:
        archived = archive.archive(image)
    except (MarketContextImageError, OSError) as exc:
        st.error(f"Görsel arşivlenemedi: {exc}")
        return ""

    reuse_note = " · mevcut arşiv kaydı kullanıldı" if archived.reused_existing else ""
    st.caption(f"Görsel arşivi: {archived.file_path}{reuse_note}")

    text_key = _session_key("text", image.sha256)
    approval_key = _session_key("approved", image.sha256)

    if text_key not in st.session_state:
        st.session_state[text_key] = ""

    if st.button(
        "Görselden metni çıkar",
        type="secondary",
        width="stretch",
        key=_session_key("extract", image.sha256),
    ):
        try:
            with st.spinner("Görseldeki metin okunuyor..."):
                extraction = GeminiMarketContextImageExtractor().extract(image)
        except (MarketContextImageExtractionError, OSError, ValueError) as exc:
            st.warning(str(exc))
        else:
            st.session_state[text_key] = extraction.text
            st.session_state[approval_key] = False
            st.session_state.pop(IMAGE_APPROVED_TEXT_KEY, None)
            st.session_state.pop(IMAGE_APPROVED_DIGEST_KEY, None)
            st.session_state.pop(IMAGE_TRANSFER_TOKEN_KEY, None)
            st.success(
                f"Metin çıkarıldı · {extraction.provider}/{extraction.model} · "
                f"{extraction.elapsed_seconds:.2f} sn"
            )

    st.text_area(
        "Çıkarılan metin — kontrol edip gerekirse düzeltin",
        key=text_key,
        height=260,
        help=(
            "AI/OCR sonucu doğrudan bağlam arşivine girmez. Metni kontrol edip "
            "aşağıdaki onayı vermeniz gerekir."
        ),
    )

    approved = st.checkbox(
        "Metni kontrol ettim; bu metnin Seans Öncesi Bağlam kaydında kullanılmasını onaylıyorum.",
        value=False,
        key=approval_key,
    )
    corrected_text = str(st.session_state.get(text_key, "")).strip()
    if not approved:
        return ""
    if not corrected_text:
        st.warning("Onay için çıkarılan/düzeltilen metin boş olmamalıdır.")
        return ""

    try:
        archive.mark_review_approved(archived, corrected_text)
    except (MarketContextImageError, OSError) as exc:
        st.error(f"Görsel inceleme onayı arşivlenemedi: {exc}")
        return ""

    st.session_state[IMAGE_APPROVED_TEXT_KEY] = corrected_text
    st.session_state[IMAGE_APPROVED_DIGEST_KEY] = image.sha256
    st.success(
        "Görsel metni kullanıcı onayıyla hazır. "
        "Aşağıdaki Bülten / haber metni alanına otomatik aktarılacaktır."
    )
    return corrected_text
