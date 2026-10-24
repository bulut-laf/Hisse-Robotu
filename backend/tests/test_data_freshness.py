from datetime import datetime, timezone

import pandas as pd

from backend.app.data.data_freshness import (
    BEKLEMEDE,
    ESKI,
    GUNCEL,
    gunluk_veri_tazeligini_degerlendir,
    toplu_veri_tazeligini_degerlendir,
)


def frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame({"Close": range(len(dates))}, index=pd.to_datetime(dates))


def test_seans_kapanisi_sonrasi_bugunun_bari_gunceldir():
    now = datetime(2026, 7, 28, 19, 0, tzinfo=timezone.utc)
    sonuc = gunluk_veri_tazeligini_degerlendir(frame("2026-07-28"), simdi=now)
    assert sonuc.durum == GUNCEL
    assert not sonuc.kilitli


def test_seans_kapanisi_sonrasi_onceki_gun_eski_veridir():
    now = datetime(2026, 7, 28, 19, 0, tzinfo=timezone.utc)
    sonuc = gunluk_veri_tazeligini_degerlendir(frame("2026-07-27"), simdi=now)
    assert sonuc.durum == ESKI
    assert sonuc.kilitli
    assert sonuc.is_gunu_gecikmesi == 1


def test_seans_icinde_onceki_islem_gunu_beklenen_degerdir():
    now = datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc)
    sonuc = gunluk_veri_tazeligini_degerlendir(frame("2026-07-27"), simdi=now)
    assert sonuc.durum == BEKLEMEDE
    assert not sonuc.kilitli


def test_hafta_sonu_cuma_bari_gunceldir():
    now = datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc)
    sonuc = gunluk_veri_tazeligini_degerlendir(frame("2026-07-31"), simdi=now)
    assert sonuc.durum == GUNCEL
    assert not sonuc.kilitli


def test_toplu_veride_tek_eski_sembol_izole_edilir_tarama_devam_eder():
    now = datetime(2026, 7, 28, 19, 0, tzinfo=timezone.utc)
    sonuc = toplu_veri_tazeligini_degerlendir(
        {"A.IS": frame("2026-07-28"), "B.IS": frame("2026-07-27")},
        simdi=now,
    )
    assert not sonuc.kilitli
    assert sonuc.guncel_sembol == 1
    assert sonuc.eski_sembol == 1
    assert sonuc.kilit_asamasi == "kısmi sembol izolasyonu"
    assert "analiz dışı bırakılmalıdır" in sonuc.aciklama


def test_eski_veri_sonraki_kontrol_zamanini_ve_asamayi_icerir():
    now = datetime(2026, 7, 28, 19, 0, tzinfo=timezone.utc)
    sonuc = gunluk_veri_tazeligini_degerlendir(
        frame("2026-07-27"),
        simdi=now,
    )

    assert sonuc.kilit_asamasi == "sağlayıcı günlük bar tazeliği"
    assert sonuc.sonraki_kontrol_zamani is not None


def test_guncel_veride_sonraki_kontrol_zamani_yoktur():
    now = datetime(2026, 7, 28, 19, 0, tzinfo=timezone.utc)
    sonuc = gunluk_veri_tazeligini_degerlendir(
        frame("2026-07-28"),
        simdi=now,
    )

    assert sonuc.sonraki_kontrol_zamani is None
    assert sonuc.kilit_asamasi == "doğrulandı"