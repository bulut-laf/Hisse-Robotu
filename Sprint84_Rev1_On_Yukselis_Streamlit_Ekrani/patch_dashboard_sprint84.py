from pathlib import Path
import sys

project_root = Path(sys.argv[1])
dashboard_path = project_root / "backend" / "dashboard.py"
source = dashboard_path.read_text(encoding="utf-8-sig")

import_line = (
    "from backend.app.ui.prebreakout_dashboard import "
    "on_yukselis_hazirlik_formu\n"
)
if import_line not in source:
    anchor = "import streamlit as st\n"
    if anchor not in source:
        raise RuntimeError("Dashboard import ekleme noktası bulunamadı.")
    source = source.replace(anchor, anchor + "\n" + import_line, 1)

if '"Ön Yükseliş Hazırlık",' not in source:
    anchor = '    "Momentum Keşif",\n'
    if anchor not in source:
        raise RuntimeError("ANALIZ_MODLARI ekleme noktası bulunamadı.")
    source = source.replace(
        anchor,
        anchor + '    "Ön Yükseliş Hazırlık",\n',
        1,
    )

dispatch = (
    '    elif analiz_modu == "Ön Yükseliş Hazırlık":\n'
    '        on_yukselis_hazirlik_formu()\n'
)
if dispatch not in source:
    anchor = (
        '    elif analiz_modu == "Momentum Keşif":\n'
        '        momentum_kesif_formu()\n'
    )
    if anchor not in source:
        raise RuntimeError("Dashboard yönlendirme ekleme noktası bulunamadı.")
    source = source.replace(anchor, anchor + dispatch, 1)

dashboard_path.write_text(source, encoding="utf-8")
