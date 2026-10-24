from pathlib import Path
import sys

project_root = Path(sys.argv[1])
dashboard_path = project_root / "backend" / "dashboard.py"
source = dashboard_path.read_text(encoding="utf-8-sig")

import_line = (
    "from backend.app.ui.prebreakout_validation_dashboard import "
    "on_yukselis_toplu_dogrulama_formu\n"
)
if import_line not in source:
    anchor = (
        "from backend.app.ui.prebreakout_dashboard import "
        "on_yukselis_hazirlik_formu\n"
    )
    if anchor not in source:
        raise RuntimeError("Sprint-87 import ekleme noktası bulunamadı.")
    source = source.replace(anchor, anchor + import_line, 1)

menu_line = '    "Ön Yükseliş Toplu Doğrulama",\n'
if menu_line not in source:
    anchor = '    "Ön Yükseliş Hazırlık",\n'
    if anchor not in source:
        raise RuntimeError("Sprint-87 menü ekleme noktası bulunamadı.")
    source = source.replace(anchor, anchor + menu_line, 1)

dispatch = (
    '    elif analiz_modu == "Ön Yükseliş Toplu Doğrulama":\n'
    '        on_yukselis_toplu_dogrulama_formu()\n'
)
if dispatch not in source:
    anchor = (
        '    elif analiz_modu == "Ön Yükseliş Hazırlık":\n'
        '        on_yukselis_hazirlik_formu()\n'
    )
    if anchor not in source:
        raise RuntimeError("Sprint-87 yönlendirme ekleme noktası bulunamadı.")
    source = source.replace(anchor, anchor + dispatch, 1)

dashboard_path.write_text(source, encoding="utf-8")
