from backend.app.ui.sprint135_dashboard_patch import patch_text

BASE = """from backend.app.analysis.momentum_walk_forward import (
    MomentumWalkForwardService,
)
from backend.app.analysis.loss_analysis import (
    LossAnalysisResult,
)

MOMENTUM_REPLAY_RESULT_KEY = "momentum_walk_forward_sonucu"

def momentum_kesif_formu() -> None:
    ozel_liste = "THYAO"
    minimum_skor = 55
    maksimum_aday = 25
    internetten_guncelle = True
    semboller = ozel_sembol_metinini_ayristir(ozel_liste)
    replay_imzasi = object()
"""

def test_patch_import_helper_call_ekler():
    patched = patch_text(BASE)
    assert "render_momentum_batch_history_panel" in patched
    assert "def momentum_toplu_tarihsel_export_goster(" in patched
    assert "semboller=tuple(semboller)" in patched

def test_patch_idempotent():
    once = patch_text(BASE)
    twice = patch_text(once)
    assert once == twice

def test_anchor_yoksa_guvenli_hata():
    with __import__("pytest").raises(RuntimeError):
        patch_text("print('x')")
