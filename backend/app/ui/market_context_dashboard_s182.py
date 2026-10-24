from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.ui.market_context_dashboard_s157 import (
    RESET_AFTER_SAVE_KEY,
    render_market_context_dashboard as _render_market_context_dashboard_s157,
)
from backend.app.ui.market_context_pdf_fallback import (
    _clear_pdf_fallback_state,
    render_scanned_pdf_fallback,
)


def render_market_context_dashboard(st: Any, *, project_root: Path) -> None:
    """Sprint-182 PDF fallback katmanını kararlı Sprint-179/S157 ekranının önüne ekler."""

    if st.session_state.get(RESET_AFTER_SAVE_KEY):
        _clear_pdf_fallback_state(st.session_state)

    # Aktarım, mevcut market_context_manual_text widget'ı yaratılmadan önce yapılabilsin diye
    # fallback kararlı S157 ekranından önce render edilir.
    render_scanned_pdf_fallback(st)
    _render_market_context_dashboard_s157(st, project_root=project_root)
