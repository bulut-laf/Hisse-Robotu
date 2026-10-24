from backend.app.ui.sprint136_dashboard_patch import patch_text

BASE = """from backend.app.ui.momentum_batch_history_integration import (
    render_momentum_batch_history_panel,
)

def momentum_toplu_tarihsel_export_goster(
    *,
    semboller: tuple[str, ...],
    minimum_skor: int,
    maksimum_aday: int,
    internetten_guncelle: bool,
) -> None:
    with st.expander("Toplu tarihsel tarama ve CSV export", expanded=False):
        render_momentum_batch_history_panel(
            st,
            minimum_skor=int(minimum_skor),
            maksimum_aday=int(maksimum_aday),
            ozel_semboller=tuple(semboller),
            internetten_guncelle=bool(internetten_guncelle),
            default_start_date=date.today() - timedelta(days=35),
            default_end_date=date.today() - timedelta(days=1),
        )
"""

def test_patch_sprint136_paneline_gecer():
    patched = patch_text(BASE)
    assert "render_sprint136_batch_panel" in patched
    assert "render_momentum_batch_history_panel" not in patched

def test_patch_idempotent():
    once = patch_text(BASE)
    assert patch_text(once) == once
