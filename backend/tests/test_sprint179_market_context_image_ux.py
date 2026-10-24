from __future__ import annotations

from datetime import date
from pathlib import Path

from backend.app.ui.market_context_dashboard_s157 import (
    FILE_UPLOAD_GENERATION_KEY,
    POST_SAVE_NOTICE_KEY,
    PROCESS_BUTTON_KEY,
    RESET_AFTER_SAVE_KEY,
    _MarketContextResetAwareStreamlitProxy,
    _apply_pending_post_save_reset,
    _reset_market_context_for_next_content,
    _transfer_approved_image_text,
)
from backend.app.ui.market_context_image_input import (
    IMAGE_APPROVED_DIGEST_KEY,
    IMAGE_TRANSFER_TOKEN_KEY,
    IMAGE_UPLOAD_GENERATION_KEY,
)


class _FakeSt:
    def __init__(self) -> None:
        self.session_state = {}
        self.success_messages = []
        self.error_messages = []
        self.warning_messages = []
        self.button_results = {}
        self.file_upload_results = {}
        self.file_upload_calls = []

    def file_uploader(self, label, *args, **kwargs):
        key = kwargs.get("key")
        self.file_upload_calls.append((label, key))
        return self.file_upload_results.get(key)

    def button(self, label, *args, **kwargs):
        return bool(self.button_results.get(kwargs.get("key"), False))

    def form_submit_button(self, label, *args, **kwargs):
        return bool(self.button_results.get(kwargs.get("key"), False))

    def success(self, body, *args, **kwargs):
        self.success_messages.append(str(body))
        return body

    def error(self, body, *args, **kwargs):
        self.error_messages.append(str(body))
        return body

    def warning(self, body, *args, **kwargs):
        self.warning_messages.append(str(body))
        return body


def test_onayli_gorsel_metni_manuel_alana_otomatik_aktarilir():
    st = _FakeSt()
    st.session_state[IMAGE_APPROVED_DIGEST_KEY] = "abc123"

    changed = _transfer_approved_image_text(st, "  BIST 100 destek 13.000  ")

    assert changed is True
    assert st.session_state["market_context_input_mode"] == "Metin Yapıştır"
    assert st.session_state["market_context_manual_text"] == "BIST 100 destek 13.000"
    assert st.session_state[IMAGE_TRANSFER_TOKEN_KEY]


def test_ayni_onayli_metin_kullanici_duzeltmesini_tekrar_ezmez():
    st = _FakeSt()
    st.session_state[IMAGE_APPROVED_DIGEST_KEY] = "abc123"
    assert _transfer_approved_image_text(st, "ilk metin") is True
    st.session_state["market_context_manual_text"] = "kullanıcının son düzeltmesi"

    changed = _transfer_approved_image_text(st, "ilk metin")

    assert changed is False
    assert st.session_state["market_context_manual_text"] == "kullanıcının son düzeltmesi"


def test_farkli_gorsel_ayni_metin_olsa_bile_yeniden_aktarilir():
    st = _FakeSt()
    st.session_state[IMAGE_APPROVED_DIGEST_KEY] = "ilk-gorsel"
    assert _transfer_approved_image_text(st, "aynı metin") is True
    st.session_state["market_context_manual_text"] = "değiştirildi"
    st.session_state[IMAGE_APPROVED_DIGEST_KEY] = "ikinci-gorsel"

    assert _transfer_approved_image_text(st, "aynı metin") is True
    assert st.session_state["market_context_manual_text"] == "aynı metin"


def test_basarili_kayit_mesaj_metnine_bagli_olmadan_reset_istegi_olusturur():
    st = _FakeSt()
    st.button_results[PROCESS_BUTTON_KEY] = True
    proxy = _MarketContextResetAwareStreamlitProxy(st)

    assert proxy.button("İçeriği İşle ve Kaydet", key=PROCESS_BUTTON_KEY) is True
    proxy.success("Rapor başarıyla arşive eklendi.")

    assert st.session_state[RESET_AFTER_SAVE_KEY] is True
    assert st.success_messages == ["Rapor başarıyla arşive eklendi."]


def test_ai_basarisi_form_resetini_tetiklemez():
    st = _FakeSt()
    proxy = _MarketContextResetAwareStreamlitProxy(st)

    proxy.success("AI toplu değerlendirmesi tamamlandı ve arşivlendi.")

    assert RESET_AFTER_SAVE_KEY not in st.session_state


def test_yeni_icerik_resetinde_tarih_korunur_girdi_alanlari_temizlenir():
    st = _FakeSt()
    selected_date = date(2026, 8, 6)
    st.session_state.update(
        {
            "market_context_date": selected_date,
            "market_context_source": "Aracı Kurum",
            "market_context_manual_text": "eski metin",
            "market_context_input_mode": "Metin Yapıştır",
            "market_context_txt_file": object(),
            "market_context_pdf_file": object(),
            "market_context_pdf_file__generation_2": object(),
            "market_context_txt_file__generation_2": object(),
            "market_context_image_text_deadbeef": "OCR",
            IMAGE_UPLOAD_GENERATION_KEY: 4,
            FILE_UPLOAD_GENERATION_KEY: 2,
        }
    )

    _reset_market_context_for_next_content(st)

    assert st.session_state["market_context_date"] == selected_date
    assert "market_context_source" not in st.session_state
    assert "market_context_manual_text" not in st.session_state
    assert "market_context_input_mode" not in st.session_state
    assert "market_context_txt_file" not in st.session_state
    assert "market_context_pdf_file" not in st.session_state
    assert "market_context_pdf_file__generation_2" not in st.session_state
    assert "market_context_txt_file__generation_2" not in st.session_state
    assert "market_context_image_text_deadbeef" not in st.session_state
    assert st.session_state[IMAGE_UPLOAD_GENERATION_KEY] == 5
    assert st.session_state[FILE_UPLOAD_GENERATION_KEY] == 3


def test_bekleyen_reset_bir_sonraki_turda_uygulanir_ve_bildirim_hazirlar():
    st = _FakeSt()
    st.session_state[RESET_AFTER_SAVE_KEY] = True
    st.session_state["market_context_source"] = "Kaynak"

    applied = _apply_pending_post_save_reset(st)

    assert applied is True
    assert RESET_AFTER_SAVE_KEY not in st.session_state
    assert "market_context_source" not in st.session_state
    assert "Yeni içerik" in st.session_state[POST_SAVE_NOTICE_KEY]


def test_wrapper_artik_sabit_basarili_kayit_mesajina_bagli_degildir():
    source = Path("backend/app/ui/market_context_dashboard_s157.py").read_text(encoding="utf-8")

    assert "market_context_image_transfer_preview" not in source
    assert "SAVE_SUCCESS_MESSAGE" not in source
    assert 'kwargs.get("key") == PROCESS_BUTTON_KEY' in source
    assert 'st.session_state["market_context_manual_text"] = clean_text' in source


def test_pdf_uploader_yeni_nesil_anahtariyla_cizilir_ve_statike_yansitilir():
    st = _FakeSt()
    st.session_state[FILE_UPLOAD_GENERATION_KEY] = 7
    uploaded = object()
    dynamic_key = "market_context_pdf_file__generation_7"
    st.file_upload_results[dynamic_key] = uploaded
    proxy = _MarketContextResetAwareStreamlitProxy(st)

    result = proxy.file_uploader(
        "PDF dosyası",
        type=("pdf",),
        key="market_context_pdf_file",
    )

    assert result is uploaded
    assert st.file_upload_calls == [("PDF dosyası", dynamic_key)]
    assert st.session_state["market_context_pdf_file"] is uploaded


def test_pdf_uploader_reset_sonrasi_farkli_widget_anahtari_kullanir():
    st = _FakeSt()
    st.session_state[FILE_UPLOAD_GENERATION_KEY] = 3
    first_key = "market_context_pdf_file__generation_3"
    st.file_upload_results[first_key] = object()
    proxy = _MarketContextResetAwareStreamlitProxy(st)

    assert proxy.file_uploader("PDF", key="market_context_pdf_file") is not None
    _reset_market_context_for_next_content(st)

    assert st.session_state[FILE_UPLOAD_GENERATION_KEY] == 4
    assert proxy.file_uploader("PDF", key="market_context_pdf_file") is None
    assert st.file_upload_calls[-1] == (
        "PDF",
        "market_context_pdf_file__generation_4",
    )
    assert "market_context_pdf_file" not in st.session_state


def test_txt_uploader_da_ayni_temiz_yeni_icerik_sozlesmesini_kullanir():
    st = _FakeSt()
    st.session_state[FILE_UPLOAD_GENERATION_KEY] = 2
    proxy = _MarketContextResetAwareStreamlitProxy(st)

    proxy.file_uploader("TXT", key="market_context_txt_file")

    assert st.file_upload_calls == [(
        "TXT",
        "market_context_txt_file__generation_2",
    )]
