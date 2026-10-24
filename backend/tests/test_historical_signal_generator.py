from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from backend.app.backtest.historical_signal_generator import (
    HistoricalSignalGenerator,
    HistoricalSignalGeneratorConfig,
    HistoricalSignalGeneratorError,
)


POZITIF = "Pozitif Teknik Görünüm"
NOTR = "Nötr Teknik Görünüm"


def fiyat_verisi_olustur(
    bar_sayisi: int = 8,
) -> pd.DataFrame:
    acilislar = [
        100.0 + konum
        for konum in range(bar_sayisi)
    ]

    kapanislar = [
        fiyat + 0.50
        for fiyat in acilislar
    ]

    return pd.DataFrame(
        {
            "Open": acilislar,
            "High": [
                fiyat + 1.0
                for fiyat in acilislar
            ],
            "Low": [
                fiyat - 1.0
                for fiyat in acilislar
            ],
            "Close": kapanislar,
            "Volume": [
                1_000_000.0
                + konum * 10_000
                for konum in range(bar_sayisi)
            ],
        },
        index=pd.date_range(
            start="2026-01-01",
            periods=bar_sayisi,
            freq="D",
        ),
    )


def analiz_sonucu(
    skor: int = 70,
    gorunum: str = POZITIF,
) -> object:
    return SimpleNamespace(
        sinyal=SimpleNamespace(
            skor=skor,
            karar=gorunum,
        )
    )


def test_yalnizca_gecmis_verisi_analize_gonderilir() -> None:
    gorulen_uzunluklar: list[int] = []
    gorulen_son_tarihler: list[date] = []

    def analiz(
        sembol: str,
        veri: pd.DataFrame,
    ) -> object:
        assert sembol == "AAA.IS"

        gorulen_uzunluklar.append(
            len(veri)
        )

        gorulen_son_tarihler.append(
            veri.index[-1].date()
        )

        return analiz_sonucu()

    sonuc = HistoricalSignalGenerator(
        analiz
    ).uret(
        sembol=" aaa.is ",
        fiyat_verisi=fiyat_verisi_olustur(
            bar_sayisi=6
        ),
        yapilandirma=(
            HistoricalSignalGeneratorConfig(
                minimum_bar_sayisi=3
            )
        ),
    )

    assert gorulen_uzunluklar == [
        3,
        4,
        5,
    ]

    assert gorulen_son_tarihler == [
        date(2026, 1, 3),
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]

    assert sonuc.sinyal_sayisi == 3
    assert sonuc.degerlendirilen_gun_sayisi == 3

    assert [
        sinyal.sinyal_tarihi
        for sinyal in sonuc.sinyaller
    ] == gorulen_son_tarihler


def test_son_bar_giris_gunu_olmadigi_icin_degerlendirilmez() -> None:
    cagrilan_tarihler: list[date] = []

    def analiz(
        sembol: str,
        veri: pd.DataFrame,
    ) -> object:
        cagrilan_tarihler.append(
            veri.index[-1].date()
        )

        return analiz_sonucu()

    HistoricalSignalGenerator(
        analiz
    ).uret(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(
            bar_sayisi=5
        ),
        yapilandirma=(
            HistoricalSignalGeneratorConfig(
                minimum_bar_sayisi=2
            )
        ),
    )

    assert cagrilan_tarihler[-1] == date(
        2026,
        1,
        4,
    )

    assert date(
        2026,
        1,
        5,
    ) not in cagrilan_tarihler


def test_tarih_araligi_uygulanir() -> None:
    sonuc = HistoricalSignalGenerator(
        lambda sembol, veri: analiz_sonucu()
    ).uret(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(
            bar_sayisi=8
        ),
        yapilandirma=(
            HistoricalSignalGeneratorConfig(
                minimum_bar_sayisi=2,
                baslangic_tarihi=date(
                    2026,
                    1,
                    4,
                ),
                bitis_tarihi=date(
                    2026,
                    1,
                    6,
                ),
            )
        ),
    )

    assert [
        sinyal.sinyal_tarihi
        for sinyal in sonuc.sinyaller
    ] == [
        date(2026, 1, 4),
        date(2026, 1, 5),
        date(2026, 1, 6),
    ]


def test_izin_verilmeyen_gorunum_atlanir() -> None:
    def analiz(
        sembol: str,
        veri: pd.DataFrame,
    ) -> object:
        gorunum = (
            POZITIF
            if len(veri) % 2 == 0
            else NOTR
        )

        return analiz_sonucu(
            gorunum=gorunum
        )

    sonuc = HistoricalSignalGenerator(
        analiz
    ).uret(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(
            bar_sayisi=6
        ),
        yapilandirma=(
            HistoricalSignalGeneratorConfig(
                minimum_bar_sayisi=2,
                izin_verilen_gorunumler=(
                    POZITIF,
                ),
            )
        ),
    )

    assert sonuc.sinyal_sayisi == 2
    assert sonuc.atlanan_gun_sayisi == 2

    assert all(
        sinyal.teknik_gorunum == POZITIF
        for sinyal in sonuc.sinyaller
    )

    assert all(
        "izin verilen" in atlanan.neden
        for atlanan in sonuc.atlanan_gunler
    )


def test_analiz_hatasi_programi_durdurmaz() -> None:
    def analiz(
        sembol: str,
        veri: pd.DataFrame,
    ) -> object:
        if len(veri) == 3:
            raise RuntimeError(
                "Örnek analiz hatası"
            )

        return analiz_sonucu()

    sonuc = HistoricalSignalGenerator(
        analiz
    ).uret(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(
            bar_sayisi=5
        ),
        yapilandirma=(
            HistoricalSignalGeneratorConfig(
                minimum_bar_sayisi=2
            )
        ),
    )

    assert sonuc.degerlendirilen_gun_sayisi == 3
    assert sonuc.sinyal_sayisi == 2
    assert sonuc.atlanan_gun_sayisi == 1
    assert "RuntimeError" in (
        sonuc.atlanan_gunler[0].neden
    )


def test_yetersiz_bar_varsa_bos_sonuc_doner() -> None:
    sonuc = HistoricalSignalGenerator(
        lambda sembol, veri: analiz_sonucu()
    ).uret(
        sembol="AAA.IS",
        fiyat_verisi=fiyat_verisi_olustur(
            bar_sayisi=3
        ),
        yapilandirma=(
            HistoricalSignalGeneratorConfig(
                minimum_bar_sayisi=5
            )
        ),
    )

    assert sonuc.sinyaller == ()
    assert sonuc.atlanan_gunler == ()
    assert sonuc.degerlendirilen_gun_sayisi == 0


def test_gecersiz_ayar_ve_fiyat_verisi_hata_verir() -> None:
    with pytest.raises(ValueError):
        HistoricalSignalGeneratorConfig(
            minimum_bar_sayisi=0
        )

    with pytest.raises(ValueError):
        HistoricalSignalGeneratorConfig(
            baslangic_tarihi=date(
                2026,
                2,
                1,
            ),
            bitis_tarihi=date(
                2026,
                1,
                1,
            ),
        )

    eksik_veri = pd.DataFrame(
        {
            "Open": [
                100.0,
                101.0,
            ],
            "Close": [
                100.5,
                101.5,
            ],
        },
        index=pd.date_range(
            start="2026-01-01",
            periods=2,
            freq="D",
        ),
    )

    with pytest.raises(
        HistoricalSignalGeneratorError,
        match="eksik",
    ):
        HistoricalSignalGenerator(
            lambda sembol, veri: analiz_sonucu()
        ).uret(
            sembol="AAA.IS",
            fiyat_verisi=eksik_veri,
        )