from __future__ import annotations

import argparse
from pathlib import Path


OLD_IMPORT = """from backend.app.ui.momentum_batch_history_integration import (
    render_momentum_batch_history_panel,
)
"""
NEW_IMPORT = """from backend.app.ui.sprint136_batch_history_ui import (
    render_sprint136_batch_panel,
)
"""

OLD_CALL = """        render_momentum_batch_history_panel(
            st,
            minimum_skor=int(minimum_skor),
            maksimum_aday=int(maksimum_aday),
            ozel_semboller=tuple(semboller),
            internetten_guncelle=bool(internetten_guncelle),
            default_start_date=date.today() - timedelta(days=35),
            default_end_date=date.today() - timedelta(days=1),
        )
"""
NEW_CALL = """        render_sprint136_batch_panel(
            st,
            minimum_skor=int(minimum_skor),
            maksimum_aday=int(maksimum_aday),
            ozel_semboller=tuple(semboller),
            internetten_guncelle=bool(internetten_guncelle),
            default_start_date=date.today() - timedelta(days=35),
            default_end_date=date.today() - timedelta(days=1),
        )
"""


def patch_text(text: str) -> str:
    if "render_sprint136_batch_panel" not in text:
        if OLD_IMPORT not in text:
            raise RuntimeError("Sprint-135 import anchor bulunamadı.")
        text = text.replace(OLD_IMPORT, NEW_IMPORT, 1)

    if "render_sprint136_batch_panel(" not in text:
        if OLD_CALL not in text:
            raise RuntimeError("Sprint-135 panel çağrısı bulunamadı.")
        text = text.replace(OLD_CALL, NEW_CALL, 1)

    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dashboard")
    args = parser.parse_args()
    path = Path(args.dashboard)
    path.write_text(
        patch_text(path.read_text(encoding="utf-8")),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
