from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from backend.app.data.data_freshness import (
    BEKLEMEDE,
    toplu_veri_tazeligini_degerlendir,
)


def _frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {"Close": range(len(dates))},
        index=pd.to_datetime(dates),
    )


def test_seans_icinde_tamamlanmis_onceki_gun_mesaji_kismi_bar_demiyor():
    now = datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc)

    sonuc = toplu_veri_tazeligini_degerlendir(
        {
            "A.IS": _frame("2026-07-27"),
            "B.IS": _frame("2026-07-27"),
        },
        simdi=now,
    )

    assert sonuc.durum == BEKLEMEDE
    assert sonuc.guncel_sembol == 2
    assert sonuc.eski_sembol == 0
    assert "Son tamamlanmış işlem günü 2026-07-27" in sonuc.aciklama
    assert "gün içi/kısmi bar teknik analize dahil edilmiyor" in sonuc.aciklama
    assert "analize yansıtılıyor" not in sonuc.aciklama


def test_seans_icinde_gercek_bugun_kismi_bari_varsa_mesaj_korunur():
    now = datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc)

    sonuc = toplu_veri_tazeligini_degerlendir(
        {
            "A.IS": _frame("2026-07-28"),
            "B.IS": _frame("2026-07-28"),
        },
        simdi=now,
    )

    assert sonuc.durum == BEKLEMEDE
    assert sonuc.guncel_sembol == 2
    assert "2 sembolde bugünkü gün içi/kısmi bar" in sonuc.aciklama
    assert "analize yansıtılıyor" in sonuc.aciklama
