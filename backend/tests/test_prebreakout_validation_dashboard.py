from pathlib import Path

import pandas as pd

from backend.app.ui.prebreakout_validation_dashboard import (
    _etiket_dagilimi_table,
    sembolleri_hazirla,
)


def test_validation_dashboard_sembolleri_duzeltir() -> None:
    assert sembolleri_hazirla(
        "thyao, ASELS.IS, thyao\nTUPRS"
    ) == ("THYAO.IS", "ASELS.IS", "TUPRS.IS")


def test_toplu_dogrulama_ekrani_evren_ve_kesim_limiti_sunar() -> None:
    source = Path(
        "backend/app/ui/prebreakout_validation_dashboard.py"
    ).read_text(encoding="utf-8")
    assert '"Evren"' in source
    assert '"Her kesimde gösterilecek sonuç"' in source
    assert "ON_YUKSELIS_EVRENLERI" in source


def test_performans_etiketi_dagilimi_uretilir() -> None:
    table = pd.DataFrame(
        {
            "performance_label": [
                "Başarılı",
                "Başarılı",
                "Sınırlı hareket",
                "Yanlış pozitif",
            ]
        }
    )

    result = _etiket_dagilimi_table(table)

    successful = result.loc[
        result["Performans etiketi"] == "Başarılı",
        "Adet",
    ].iloc[0]
    assert successful == 2


def test_bos_etiket_tablosu_guvenli_sonuc_uretir() -> None:
    result = _etiket_dagilimi_table(pd.DataFrame())

    assert list(result.columns) == ["Performans etiketi", "Adet"]
    assert result.empty
