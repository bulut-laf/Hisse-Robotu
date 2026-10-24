from __future__ import annotations

from backend.app.ui.market_context_pdf_fallback import (
    PDF_FALLBACK_DIGEST_KEY,
    PDF_FALLBACK_TEXT_KEY,
    PDF_FALLBACK_TRANSFER_TOKEN_KEY,
    PDF_FALLBACK_UPLOAD_GENERATION_KEY,
    PDF_FALLBACK_UPLOAD_PREFIX,
    _clear_pdf_fallback_state,
    _transfer_approved_pdf_text,
)


def test_approved_pdf_text_transfers_to_existing_manual_market_context():
    state = {
        PDF_FALLBACK_DIGEST_KEY: "abc",
        PDF_FALLBACK_TEXT_KEY: "BIST 100 13.700 desteğini izliyor.",
    }
    assert _transfer_approved_pdf_text(state) is True
    assert state["market_context_input_mode"] == "Metin Yapıştır"
    assert state["market_context_manual_text"] == "BIST 100 13.700 desteğini izliyor."


def test_same_pdf_transfer_does_not_overwrite_user_edit():
    state = {
        PDF_FALLBACK_DIGEST_KEY: "abc",
        PDF_FALLBACK_TEXT_KEY: "İlk metin",
    }
    assert _transfer_approved_pdf_text(state) is True
    state["market_context_manual_text"] = "Kullanıcı düzenledi"
    assert _transfer_approved_pdf_text(state) is False
    assert state["market_context_manual_text"] == "Kullanıcı düzenledi"


def test_new_pdf_digest_can_transfer_new_text():
    state = {
        PDF_FALLBACK_DIGEST_KEY: "abc",
        PDF_FALLBACK_TEXT_KEY: "İlk metin",
    }
    assert _transfer_approved_pdf_text(state) is True
    state[PDF_FALLBACK_DIGEST_KEY] = "xyz"
    state[PDF_FALLBACK_TEXT_KEY] = "Yeni PDF metni"
    assert _transfer_approved_pdf_text(state) is True
    assert state["market_context_manual_text"] == "Yeni PDF metni"


def test_post_save_clear_resets_fallback_state_and_uploader_generation():
    state = {
        PDF_FALLBACK_UPLOAD_GENERATION_KEY: 4,
        PDF_FALLBACK_DIGEST_KEY: "abc",
        PDF_FALLBACK_TEXT_KEY: "metin",
        PDF_FALLBACK_TRANSFER_TOKEN_KEY: "token",
        f"{PDF_FALLBACK_UPLOAD_PREFIX}4": object(),
        "market_context_date": "2026-08-10",
    }
    _clear_pdf_fallback_state(state)
    assert state[PDF_FALLBACK_UPLOAD_GENERATION_KEY] == 5
    assert PDF_FALLBACK_DIGEST_KEY not in state
    assert PDF_FALLBACK_TEXT_KEY not in state
    assert PDF_FALLBACK_TRANSFER_TOKEN_KEY not in state
    assert f"{PDF_FALLBACK_UPLOAD_PREFIX}4" not in state
    assert state["market_context_date"] == "2026-08-10"
