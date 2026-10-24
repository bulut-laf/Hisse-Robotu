from __future__ import annotations

import hashlib
from pathlib import Path

from backend.app.ui.market_context_dashboard import (
    render_market_context_dashboard as _render_existing_market_context_dashboard,
)
from backend.app.ui.market_context_image_input import (
    IMAGE_APPROVED_DIGEST_KEY,
    IMAGE_TRANSFER_TOKEN_KEY,
    IMAGE_UPLOAD_GENERATION_KEY,
    render_market_context_image_input,
)
from backend.app.ui.daily_market_briefing_panel import (
    render_daily_market_briefing_panel,
)


RESET_AFTER_SAVE_KEY = "market_context_reset_after_save_requested"
POST_SAVE_NOTICE_KEY = "market_context_post_save_notice"
PROCESS_BUTTON_KEY = "market_context_process"
FILE_UPLOAD_GENERATION_KEY = "market_context_file_upload_generation"

_FILE_UPLOAD_WIDGET_KEYS = {
    "market_context_txt_file",
    "market_context_pdf_file",
}

_BASE_INPUT_KEYS = (
    "market_context_source",
    "market_context_manual_text",
    "market_context_input_mode",
    "market_context_txt_file",
    "market_context_pdf_file",
    "market_context_process",
)


class _MarketContextResetAwareStreamlitProxy:
    """Başarılı kayıt eylemini mesaj metnine bağımlı olmadan algılar."""

    def __init__(self, st) -> None:
        self._st = st
        self._process_requested = False

    def __getattr__(self, name):
        return getattr(self._st, name)

    def button(self, label, *args, **kwargs):
        result = self._st.button(label, *args, **kwargs)
        if kwargs.get("key") == PROCESS_BUTTON_KEY and bool(result):
            self._process_requested = True
        return result

    def form_submit_button(self, label, *args, **kwargs):
        result = self._st.form_submit_button(label, *args, **kwargs)
        if kwargs.get("key") == PROCESS_BUTTON_KEY and bool(result):
            self._process_requested = True
        return result

    def file_uploader(self, label, *args, **kwargs):
        original_key = kwargs.get("key")
        if original_key not in _FILE_UPLOAD_WIDGET_KEYS:
            return self._st.file_uploader(label, *args, **kwargs)

        try:
            generation = int(
                self._st.session_state.get(FILE_UPLOAD_GENERATION_KEY, 0) or 0
            )
        except (TypeError, ValueError):
            generation = 0

        forwarded = dict(kwargs)
        forwarded["key"] = f"{original_key}__generation_{max(generation, 0)}"
        uploaded = self._st.file_uploader(label, *args, **forwarded)

        # Eski dashboard kodu statik anahtarı okursa geriye dönük uyumluluk sürer.
        if uploaded is None:
            self._st.session_state.pop(original_key, None)
        else:
            self._st.session_state[original_key] = uploaded
        return uploaded

    def success(self, body, *args, **kwargs):
        result = self._st.success(body, *args, **kwargs)
        if self._process_requested:
            self._st.session_state[RESET_AFTER_SAVE_KEY] = True
            self._process_requested = False
        return result

    def error(self, body, *args, **kwargs):
        result = self._st.error(body, *args, **kwargs)
        if self._process_requested:
            self._process_requested = False
        return result

    def warning(self, body, *args, **kwargs):
        result = self._st.warning(body, *args, **kwargs)
        if self._process_requested:
            self._process_requested = False
        return result


def _approved_transfer_token(st, approved_text: str) -> str:
    digest = str(st.session_state.get(IMAGE_APPROVED_DIGEST_KEY, "") or "")
    payload = f"{digest}\0{approved_text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _transfer_approved_image_text(st, approved_text: str) -> bool:
    """Onaylı görsel metnini mevcut manuel metin widget'ına bir kez aktarır."""

    clean_text = str(approved_text or "").strip()
    if not clean_text:
        return False

    token = _approved_transfer_token(st, clean_text)
    if st.session_state.get(IMAGE_TRANSFER_TOKEN_KEY) == token:
        return False

    # Mevcut dashboard widget'ları henüz çizilmediği için bu atama güvenlidir.
    st.session_state["market_context_input_mode"] = "Metin Yapıştır"
    st.session_state["market_context_manual_text"] = clean_text
    st.session_state[IMAGE_TRANSFER_TOKEN_KEY] = token
    return True


def _reset_market_context_for_next_content(st) -> None:
    """Başarılı kayıttan sonra bir sonraki içerik için formu temizler.

    Tarih korunur; aynı seans gününde arka arkaya birden fazla rapor yükleme
    akışı hızlandırılır. Kaynak, içerik ve dosya/görsel widget durumları temizlenir.
    """

    try:
        image_generation = int(
            st.session_state.get(IMAGE_UPLOAD_GENERATION_KEY, 0) or 0
        )
    except (TypeError, ValueError):
        image_generation = 0
    try:
        file_generation = int(
            st.session_state.get(FILE_UPLOAD_GENERATION_KEY, 0) or 0
        )
    except (TypeError, ValueError):
        file_generation = 0

    for key in list(st.session_state.keys()):
        key_text = str(key)
        if (
            key_text in _BASE_INPUT_KEYS
            or key_text.startswith("market_context_image_")
            or key_text.startswith("market_context_txt_file__generation_")
            or key_text.startswith("market_context_pdf_file__generation_")
        ):
            st.session_state.pop(key, None)

    st.session_state[IMAGE_UPLOAD_GENERATION_KEY] = max(image_generation, 0) + 1
    st.session_state[FILE_UPLOAD_GENERATION_KEY] = max(file_generation, 0) + 1


def _apply_pending_post_save_reset(st) -> bool:
    if not bool(st.session_state.pop(RESET_AFTER_SAVE_KEY, False)):
        return False

    _reset_market_context_for_next_content(st)
    st.session_state[POST_SAVE_NOTICE_KEY] = (
        "İçerik kaydedildi. Yeni içerik için kaynak, metin, TXT/PDF ve görsel alanları temizlendi."
    )
    return True


def render_market_context_dashboard(st, *, project_root: Path) -> None:
    """Seans Öncesi Bağlam görsel girişini mevcut kayıt akışına bağlar.

    - Görsel metni kullanıcı onayından sonra manuel metin alanına otomatik aktarılır.
    - Başarılı kayıt sonrası bir sonraki içerik için giriş alanları otomatik temizlenir.
    - TXT/PDF yükleyicileri yeni widget nesliyle yeniden oluşturulur; eski dosya görünmez.
    - Tarih ve mevcut arşiv/AI davranışları korunur.
    """

    _apply_pending_post_save_reset(st)

    notice = st.session_state.pop(POST_SAVE_NOTICE_KEY, None)
    if notice:
        st.success(str(notice))

    with st.expander(
        "JPG / PNG ekran görüntüsü (WhatsApp vb.)",
        expanded=False,
    ):
        approved_text = render_market_context_image_input(
            st,
            project_root=project_root,
        )
        if approved_text and _transfer_approved_image_text(st, approved_text):
            st.success(
                "Onaylı görsel metni aşağıdaki Bülten / haber metni alanına otomatik aktarıldı. "
                "Kaynak ve tarihi kontrol edip İçeriği İşle ve Kaydet düğmesini kullanın."
            )

    proxy = _MarketContextResetAwareStreamlitProxy(st)
    _render_existing_market_context_dashboard(
        proxy,
        project_root=project_root,
    )

    render_daily_market_briefing_panel(
        st,
        project_root=project_root,
    )

    if st.session_state.get(RESET_AFTER_SAVE_KEY):
        # Widget anahtarları aynı turda değiştirilemez. Temizlik bir sonraki turda,
        # widget'lar çizilmeden önce yapılır.
        st.rerun()
