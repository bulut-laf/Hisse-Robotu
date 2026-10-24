from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from backend.app.backtest.backtest_engine import (
    BacktestEngine,
    BacktestEngineError,
)
from backend.app.backtest.backtest_models import (
    BacktestConfig,
    BacktestSignal,
    CIKIS_HEDEF,
    CIKIS_SURE_SONU,
    CIKIS_VERI_SONU,
    CIKIS_ZARAR_DURDUR,
)


def fiyat_verisi_olustur(
    acilislar: list[float],
    yuksekler: list[float],
    dusukler: list[float],
    kapanislar: list[float],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": acilislar,
            "High": yuksekler,
            "Low": dusukler,
            "Close": kapanislar,
        },
        index=pd.date_range(
            start="2026-01-01",
            periods=len(acilislar),
            freq="D",
        ),
    )


def sinyal_olustur(
    skor: int = 70,
    sembol: str = "AAA.IS",
    sinyal_gunu: int = 1,
) -> BacktestSignal:
    return BacktestSignal(
        sembol=sembol,
        sinyal_tarihi=date(
            2026,
            1,
            sinyal_gunu,
        ),
        skor=skor,
        teknik_gorunum=(
            "Pozitif Teknik Görünüm"
        ),
    )


def test_sinyalden_sonraki_gun_acilistan_giris_yapilir() -> None:
    veri = fiyat_verisi_olustur(
        acilislar=[
            99.0,
            100.0,
            102.0,
            104.0,
        ],
        yuksekler=[
            101.0,
            103.0,
            105.0,
            107.0,
        ],
        dusukler=[
            98.0,
            99.0,
            101.0,
            103.0,
        ],
        kapanislar=[
            100.0,
            102.0,
            104.0,
            106.0,
        ],
    )

    sonuc = BacktestEngine().calistir(
        veriler={
            "AAA.IS": veri,
        },
        sinyaller=(
            sinyal_olustur(),
        ),
        yapilandirma=BacktestConfig(
            elde_tutma_gunu=2,
            minimum_skor=50,
            islem_maliyeti_orani=0.0,
        ),
    )

    assert sonuc.tamamlanan_islem_sayisi == 1
    assert sonuc.atlanan_sinyal_sayisi == 0

    islem = sonuc.islemler[0]

    assert islem.giris_tarihi == date(
        2026,
        1,
        2,
    )
    assert islem.giris_fiyati == pytest.approx(
        100.0
    )
    assert islem.cikis_tarihi == date(
        2026,
        1,
        3,
    )
    assert islem.cikis_fiyati == pytest.approx(
        104.0
    )
    assert islem.elde_tutulan_bar == 2
    assert islem.cikis_nedeni == CIKIS_SURE_SONU


def test_minimum_skorun_altindaki_sinyal_atlanir() -> None:
    veri = fiyat_verisi_olustur(
        acilislar=[
            100.0,
            101.0,
        ],
        yuksekler=[
            102.0,
            103.0,
        ],
        dusukler=[
            99.0,
            100.0,
        ],
        kapanislar=[
            101.0,
            102.0,
        ],
    )

    sonuc = BacktestEngine().calistir(
        veriler={
            "AAA.IS": veri,
        },
        sinyaller=(
            sinyal_olustur(
                skor=40
            ),
        ),
        yapilandirma=BacktestConfig(
            minimum_skor=50
        ),
    )

    assert sonuc.tamamlanan_islem_sayisi == 0
    assert sonuc.atlanan_sinyal_sayisi == 1
    assert "minimum 50" in (
        sonuc.atlanan_sinyaller[0].neden
    )


def test_zarar_durdur_seviyesinde_cikis_yapilir() -> None:
    veri = fiyat_verisi_olustur(
        acilislar=[
            100.0,
            100.0,
            97.0,
        ],
        yuksekler=[
            102.0,
            102.0,
            99.0,
        ],
        dusukler=[
            99.0,
            94.0,
            95.0,
        ],
        kapanislar=[
            101.0,
            96.0,
            98.0,
        ],
    )

    sonuc = BacktestEngine().calistir(
        veriler={
            "AAA.IS": veri,
        },
        sinyaller=(
            sinyal_olustur(),
        ),
        yapilandirma=BacktestConfig(
            elde_tutma_gunu=2,
            zarar_durdur_orani=0.05,
            hedef_orani=0.10,
            islem_maliyeti_orani=0.0,
        ),
    )

    islem = sonuc.islemler[0]

    assert islem.cikis_fiyati == pytest.approx(
        95.0
    )
    assert islem.cikis_tarihi == date(
        2026,
        1,
        2,
    )
    assert (
        islem.cikis_nedeni
        == CIKIS_ZARAR_DURDUR
    )


def test_hedef_seviyesinde_cikis_yapilir() -> None:
    veri = fiyat_verisi_olustur(
        acilislar=[
            100.0,
            100.0,
            104.0,
        ],
        yuksekler=[
            102.0,
            106.0,
            108.0,
        ],
        dusukler=[
            99.0,
            99.0,
            103.0,
        ],
        kapanislar=[
            101.0,
            105.0,
            107.0,
        ],
    )

    sonuc = BacktestEngine().calistir(
        veriler={
            "AAA.IS": veri,
        },
        sinyaller=(
            sinyal_olustur(),
        ),
        yapilandirma=BacktestConfig(
            elde_tutma_gunu=2,
            zarar_durdur_orani=0.05,
            hedef_orani=0.05,
            islem_maliyeti_orani=0.0,
        ),
    )

    islem = sonuc.islemler[0]

    assert islem.cikis_fiyati == pytest.approx(
        105.0
    )
    assert islem.cikis_tarihi == date(
        2026,
        1,
        2,
    )
    assert islem.cikis_nedeni == CIKIS_HEDEF


def test_ayni_barda_stop_ve_hedef_gorulurse_stop_secilir() -> None:
    veri = fiyat_verisi_olustur(
        acilislar=[
            100.0,
            100.0,
        ],
        yuksekler=[
            102.0,
            106.0,
        ],
        dusukler=[
            99.0,
            94.0,
        ],
        kapanislar=[
            101.0,
            102.0,
        ],
    )

    sonuc = BacktestEngine().calistir(
        veriler={
            "AAA.IS": veri,
        },
        sinyaller=(
            sinyal_olustur(),
        ),
        yapilandirma=BacktestConfig(
            elde_tutma_gunu=1,
            zarar_durdur_orani=0.05,
            hedef_orani=0.05,
            islem_maliyeti_orani=0.0,
        ),
    )

    islem = sonuc.islemler[0]

    assert islem.cikis_fiyati == pytest.approx(
        95.0
    )
    assert (
        islem.cikis_nedeni
        == CIKIS_ZARAR_DURDUR
    )


def test_yeterli_bar_yoksa_veri_sonunda_cikis_yapilir() -> None:
    veri = fiyat_verisi_olustur(
        acilislar=[
            100.0,
            101.0,
            102.0,
        ],
        yuksekler=[
            102.0,
            103.0,
            105.0,
        ],
        dusukler=[
            99.0,
            100.0,
            101.0,
        ],
        kapanislar=[
            101.0,
            102.0,
            104.0,
        ],
    )

    sonuc = BacktestEngine().calistir(
        veriler={
            "AAA.IS": veri,
        },
        sinyaller=(
            sinyal_olustur(),
        ),
        yapilandirma=BacktestConfig(
            elde_tutma_gunu=10,
            islem_maliyeti_orani=0.0,
        ),
    )

    islem = sonuc.islemler[0]

    assert islem.cikis_tarihi == date(
        2026,
        1,
        3,
    )
    assert islem.cikis_fiyati == pytest.approx(
        104.0
    )
    assert islem.elde_tutulan_bar == 2
    assert islem.cikis_nedeni == CIKIS_VERI_SONU


def test_eksik_sembol_ve_giris_bari_olmayan_sinyaller_atlanir() -> None:
    veri = fiyat_verisi_olustur(
        acilislar=[
            100.0,
            101.0,
        ],
        yuksekler=[
            102.0,
            103.0,
        ],
        dusukler=[
            99.0,
            100.0,
        ],
        kapanislar=[
            101.0,
            102.0,
        ],
    )

    sonuc = BacktestEngine().calistir(
        veriler={
            "AAA.IS": veri,
        },
        sinyaller=(
            sinyal_olustur(
                sembol="YOK.IS",
                sinyal_gunu=1,
            ),
            sinyal_olustur(
                sembol="AAA.IS",
                sinyal_gunu=2,
            ),
        ),
        yapilandirma=BacktestConfig(
            minimum_skor=50
        ),
    )

    assert sonuc.tamamlanan_islem_sayisi == 0
    assert sonuc.atlanan_sinyal_sayisi == 2

    nedenler = tuple(
        atlanan.neden
        for atlanan in sonuc.atlanan_sinyaller
    )

    assert any(
        "fiyat verisi bulunamadı" in neden
        for neden in nedenler
    )

    assert any(
        "giriş yapılabilecek" in neden
        for neden in nedenler
    )


def test_gecersiz_fiyat_verisi_hata_verir() -> None:
    eksik_sutunlu_veri = pd.DataFrame(
        {
            "Open": [
                100.0,
                101.0,
            ],
            "Close": [
                101.0,
                102.0,
            ],
        },
        index=pd.date_range(
            start="2026-01-01",
            periods=2,
            freq="D",
        ),
    )

    with pytest.raises(
        BacktestEngineError,
        match="eksik",
    ):
        BacktestEngine().calistir(
            veriler={
                "AAA.IS": eksik_sutunlu_veri,
            },
            sinyaller=(),
            yapilandirma=BacktestConfig(),
        )