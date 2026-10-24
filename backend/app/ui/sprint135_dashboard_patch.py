from __future__ import annotations

import argparse
from pathlib import Path


IMPORT_MARKER = "from backend.app.analysis.loss_analysis import ("
IMPORT_BLOCK = """from backend.app.ui.momentum_batch_history_integration import (
    render_momentum_batch_history_panel,
)
"""

HELPER_MARKER = 'MOMENTUM_REPLAY_RESULT_KEY = "momentum_walk_forward_sonucu"'
HELPER_BLOCK = """def momentum_toplu_tarihsel_export_goster(
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

CALL_MARKER = "    semboller = ozel_sembol_metinini_ayristir(ozel_liste)\n"
CALL_BLOCK = """    semboller = ozel_sembol_metinini_ayristir(ozel_liste)
    momentum_toplu_tarihsel_export_goster(
        semboller=tuple(semboller),
        minimum_skor=int(minimum_skor),
        maksimum_aday=int(maksimum_aday),
        internetten_guncelle=bool(internetten_guncelle),
    )
"""


def patch_text(text: str) -> str:
    if "render_momentum_batch_history_panel" not in text:
        count = text.count(IMPORT_MARKER)
        if count != 1:
            raise RuntimeError(f"Import anchor beklenen 1 adet, bulunan {count}.")
        text = text.replace(IMPORT_MARKER, IMPORT_BLOCK + IMPORT_MARKER, 1)

    if "def momentum_toplu_tarihsel_export_goster(" not in text:
        count = text.count(HELPER_MARKER)
        if count != 1:
            raise RuntimeError(f"Helper anchor beklenen 1 adet, bulunan {count}.")
        text = text.replace(HELPER_MARKER, HELPER_BLOCK + HELPER_MARKER, 1)

    if "    momentum_toplu_tarihsel_export_goster(\n" not in text:
        count = text.count(CALL_MARKER)
        if count != 1:
            raise RuntimeError(f"Momentum sembol anchor beklenen 1 adet, bulunan {count}.")
        text = text.replace(CALL_MARKER, CALL_BLOCK, 1)

    return text


def patch_file(path: Path) -> None:
    original = path.read_text(encoding="utf-8")
    path.write_text(patch_text(original), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dashboard")
    args = parser.parse_args()
    patch_file(Path(args.dashboard))


if __name__ == "__main__":
    main()
