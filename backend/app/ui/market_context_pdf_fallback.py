from __future__ import annotations

import hashlib
from typing import Any, MutableMapping

from backend.app.market_context.pdf_image_fallback import (
    MAX_PDF_BYTES,
    PdfImageFallbackError,
    extract_scanned_pdf_text,
)

PDF_FALLBACK_UPLOAD_GENERATION_KEY = "market_context_pdf_fallback_upload_generation"
PDF_FALLBACK_DIGEST_KEY = "market_context_pdf_fallback_digest"
PDF_FALLBACK_TEXT_KEY = "market_context_pdf_fallback_text"
PDF_FALLBACK_PROVIDER_KEY = "market_context_pdf_fallback_provider"
PDF_FALLBACK_MODEL_KEY = "market_context_pdf_fallback_model"
PDF_FALLBACK_ELAPSED_KEY = "market_context_pdf_fallback_elapsed"
PDF_FALLBACK_TRANSFER_TOKEN_KEY = "market_context_pdf_fallback_transfer_token"
PDF_FALLBACK_UPLOAD_PREFIX = "market_context_pdf_fallback_file__generation_"
PDF_FALLBACK_CONSENT_PREFIX = "market_context_pdf_fallback_consent__generation_"


def _session(st: Any) -> MutableMapping[str, Any]:
    return st.session_state


def _clear_pdf_fallback_state(session_state: MutableMapping[str, Any]) -> None:
    generation = int(session_state.get(PDF_FALLBACK_UPLOAD_GENERATION_KEY, 0)) + 1
    removable = (
        PDF_FALLBACK_DIGEST_KEY,
        PDF_FALLBACK_TEXT_KEY,
        PDF_FALLBACK_PROVIDER_KEY,
        PDF_FALLBACK_MODEL_KEY,
        PDF_FALLBACK_ELAPSED_KEY,
        PDF_FALLBACK_TRANSFER_TOKEN_KEY,
    )
    for key in removable:
        session_state.pop(key, None)
    for key in tuple(session_state.keys()):
        if str(key).startswith(PDF_FALLBACK_UPLOAD_PREFIX) or str(key).startswith(PDF_FALLBACK_CONSENT_PREFIX):
            session_state.pop(key, None)
    session_state[PDF_FALLBACK_UPLOAD_GENERATION_KEY] = generation


def _transfer_approved_pdf_text(session_state: MutableMapping[str, Any]) -> bool:
    text = str(session_state.get(PDF_FALLBACK_TEXT_KEY, "") or "").strip()
    digest = str(session_state.get(PDF_FALLBACK_DIGEST_KEY, "") or "").strip()
    if not text or not digest:
        return False
    token = digest + ":" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    if session_state.get(PDF_FALLBACK_TRANSFER_TOKEN_KEY) == token:
        return False
    session_state["market_context_input_mode"] = "Metin Yapıştır"
    session_state["market_context_manual_text"] = text
    session_state[PDF_FALLBACK_TRANSFER_TOKEN_KEY] = token
    return True


def _reset_result_for_new_digest(session_state: MutableMapping[str, Any], digest: str) -> None:
    if session_state.get(PDF_FALLBACK_DIGEST_KEY) == digest:
        return
    session_state[PDF_FALLBACK_DIGEST_KEY] = digest
    session_state.pop(PDF_FALLBACK_TEXT_KEY, None)
    session_state.pop(PDF_FALLBACK_PROVIDER_KEY, None)
    session_state.pop(PDF_FALLBACK_MODEL_KEY, None)
    session_state.pop(PDF_FALLBACK_ELAPSED_KEY, None)


def render_scanned_pdf_fallback(st: Any) -> None:
    """Mevcut PDF yoluna dokunmadan, taranmış PDF için açık kullanıcı onaylı fallback gösterir."""

    state = _session(st)
    generation = int(state.get(PDF_FALLBACK_UPLOAD_GENERATION_KEY, 0))
    upload_key = f"{PDF_FALLBACK_UPLOAD_PREFIX}{generation}"
    consent_key = f"{PDF_FALLBACK_CONSENT_PREFIX}{generation}"

    with st.expander("Görüntü tabanlı PDF fallback — taranmış PDF", expanded=False):
        st.caption(
            "Normal metin katmanlı PDF için mevcut PDF Yükle yolunu kullanın. "
            "Bu bölüm yalnız taranmış/görüntü tabanlı PDF metni çıkarılamadığında kullanılır. "
            "PDF Gemini'ye yalnız sizin açık onayınızla gönderilir; sonuç kaydedilmeden önce önizlenir."
        )
        uploaded = st.file_uploader(
            "Taranmış PDF",
            type=("pdf",),
            accept_multiple_files=False,
            key=upload_key,
            help=f"Fallback sınırı: en fazla {MAX_PDF_BYTES // (1024 * 1024)} MB.",
        )

        pdf_bytes = b""
        if uploaded is not None:
            pdf_bytes = uploaded.getvalue()
            digest = hashlib.sha256(pdf_bytes).hexdigest() if pdf_bytes else ""
            if digest:
                _reset_result_for_new_digest(state, digest)
            st.caption(f"Dosya: {uploaded.name} · {len(pdf_bytes) / (1024 * 1024):.2f} MB")

        consent = st.checkbox(
            "Bu PDF'yi metin çıkarmak için Gemini'ye gönder",
            value=False,
            key=consent_key,
        )
        if st.button(
            "Görüntü PDF metnini çıkar",
            key=f"market_context_pdf_fallback_extract__generation_{generation}",
            disabled=(uploaded is None or not consent),
            width="stretch",
        ):
            try:
                result = extract_scanned_pdf_text(
                    pdf_bytes,
                    filename=getattr(uploaded, "name", "taranmis-belge.pdf"),
                )
            except PdfImageFallbackError as exc:
                st.error(str(exc))
            else:
                if not result.ok:
                    st.error(result.error or "Görüntü tabanlı PDF metni çıkarılamadı.")
                else:
                    state[PDF_FALLBACK_DIGEST_KEY] = result.digest
                    state[PDF_FALLBACK_TEXT_KEY] = result.text
                    state[PDF_FALLBACK_PROVIDER_KEY] = result.provider
                    state[PDF_FALLBACK_MODEL_KEY] = result.model
                    state[PDF_FALLBACK_ELAPSED_KEY] = result.elapsed_seconds
                    st.success("PDF görsel metni çıkarıldı. Kaydetmeden önce metni kontrol edin.")

        extracted = str(state.get(PDF_FALLBACK_TEXT_KEY, "") or "").strip()
        if extracted:
            provider = state.get(PDF_FALLBACK_PROVIDER_KEY, "gemini")
            model = state.get(PDF_FALLBACK_MODEL_KEY, "")
            elapsed = state.get(PDF_FALLBACK_ELAPSED_KEY, 0.0)
            st.caption(f"Sağlayıcı: {provider} · Model: {model} · Süre: {elapsed} sn")
            st.text_area(
                "Çıkarılan PDF metni — önizleme",
                value=extracted,
                height=280,
                disabled=True,
                key=f"market_context_pdf_fallback_preview__generation_{generation}",
            )
            st.warning(
                "Aktarmadan önce özellikle rakamları, yüzdeleri, tarihleri ve destek/direnç seviyelerini gözle kontrol edin."
            )
            if st.button(
                "Bu metni Bülten / haber metnine aktar",
                key=f"market_context_pdf_fallback_transfer__generation_{generation}",
                type="primary",
                width="stretch",
            ):
                if _transfer_approved_pdf_text(state):
                    st.success("PDF metni mevcut Seans Öncesi Bağlam metin alanına aktarıldı.")
                    rerun = getattr(st, "rerun", None)
                    if callable(rerun):
                        rerun()
                else:
                    st.info("Bu PDF metni zaten aktarılmış veya aktarılabilir metin bulunmuyor.")
