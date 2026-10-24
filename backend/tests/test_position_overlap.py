from __future__ import annotations

from datetime import date

import pytest

from backend.app.backtest.backtest_engine import (
    BacktestResult,
    SkippedSignal,
)
from backend.app.backtest.backtest_models import (
    BacktestConfig,
    BacktestMetrics,
    BacktestSignal,
    BacktestTrade,
    CIKIS_SURE_SONU,
)
from backend.app.backtest.position_overlap import (
    CAKISMA_NEDENI,
    cakisan_islemleri_filtrele,
)


GORUNUM = "Pozitif Teknik Görünüm"


def islem_olustur(
    sembol: str,
    sinyal_tarihi: date,
    giris_tarihi: date,
    cikis_tarihi: date,
    cikis_fiyati: float,
) -> BacktestTrade:
    return BacktestTrade.olustur(
        sembol=sembol,
        sinyal_tarihi=sinyal_tarihi,
        giris_tarihi=giris_tarihi,
        cikis_tarihi=cikis_tarihi,
        giris_fiyati=100.0,
        cikis_fiyati=cikis_fiyati,
        skor=70,
        teknik_gorunum=GORUNUM,
        elde_tutulan_bar=1,
        cikis_nedeni=CIKIS_SURE_SONU,
        islem_maliyeti_orani=0.0,
    )


def sonuc_olustur(
    islemler: tuple[BacktestTrade, ...],
    atlananlar: tuple[
        SkippedSignal,
        ...
    ] = (),
) -> tuple[
    BacktestResult,
    BacktestConfig,
]:
    yapilandirma = BacktestConfig(
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=1.0,
        islem_maliyeti_orani=0.0,
    )

    metrikler = BacktestMetrics.hesapla(
        islemler=islemler,
        yapilandirma=yapilandirma,
    )

    return (
        BacktestResult(
            islemler=islemler,
            atlanan_sinyaller=atlananlar,
            metrikler=metrikler,
        ),
        yapilandirma,
    )


def test_ayni_sembolde_cakisan_islem_atlanir() -> None:
    birinci = islem_olustur(
        sembol="AAA.IS",
        sinyal_tarihi=date(2026, 1, 1),
        giris_tarihi=date(2026, 1, 2),
        cikis_tarihi=date(2026, 1, 5),
        cikis_fiyati=110.0,
    )

    cakisan = islem_olustur(
        sembol="AAA.IS",
        sinyal_tarihi=date(2026, 1, 2),
        giris_tarihi=date(2026, 1, 3),
        cikis_tarihi=date(2026, 1, 4),
        cikis_fiyati=120.0,
    )

    pozisyon_sonrasi = islem_olustur(
        sembol="AAA.IS",
        sinyal_tarihi=date(2026, 1, 5),
        giris_tarihi=date(2026, 1, 6),
        cikis_tarihi=date(2026, 1, 7),
        cikis_fiyati=95.0,
    )

    ham_sonuc, yapilandirma = sonuc_olustur(
        (
            birinci,
            cakisan,
            pozisyon_sonrasi,
        )
    )

    sonuc = cakisan_islemleri_filtrele(
        sonuc=ham_sonuc,
        yapilandirma=yapilandirma,
    )

    assert sonuc.islemler == (
        birinci,
        pozisyon_sonrasi,
    )

    assert sonuc.tamamlanan_islem_sayisi == 2
    assert sonuc.atlanan_sinyal_sayisi == 1

    assert CAKISMA_NEDENI in (
        sonuc.atlanan_sinyaller[0].neden
    )


def test_farkli_sembollerdeki_islemler_cakisma_sayilmaz() -> None:
    aaa = islem_olustur(
        sembol="AAA.IS",
        sinyal_tarihi=date(2026, 1, 1),
        giris_tarihi=date(2026, 1, 2),
        cikis_tarihi=date(2026, 1, 5),
        cikis_fiyati=110.0,
    )

    bbb = islem_olustur(
        sembol="BBB.IS",
        sinyal_tarihi=date(2026, 1, 1),
        giris_tarihi=date(2026, 1, 2),
        cikis_tarihi=date(2026, 1, 5),
        cikis_fiyati=105.0,
    )

    ham_sonuc, yapilandirma = sonuc_olustur(
        (
            aaa,
            bbb,
        )
    )

    sonuc = cakisan_islemleri_filtrele(
        sonuc=ham_sonuc,
        yapilandirma=yapilandirma,
    )

    assert sonuc.islemler == (
        aaa,
        bbb,
    )

    assert sonuc.atlanan_sinyaller == ()


def test_cikis_gunu_baslayan_islem_temkinli_olarak_atlanir() -> None:
    birinci = islem_olustur(
        sembol="AAA.IS",
        sinyal_tarihi=date(2026, 1, 1),
        giris_tarihi=date(2026, 1, 2),
        cikis_tarihi=date(2026, 1, 5),
        cikis_fiyati=110.0,
    )

    ayni_gun_giris = islem_olustur(
        sembol="AAA.IS",
        sinyal_tarihi=date(2026, 1, 4),
        giris_tarihi=date(2026, 1, 5),
        cikis_tarihi=date(2026, 1, 7),
        cikis_fiyati=105.0,
    )

    ham_sonuc, yapilandirma = sonuc_olustur(
        (
            birinci,
            ayni_gun_giris,
        )
    )

    sonuc = cakisan_islemleri_filtrele(
        sonuc=ham_sonuc,
        yapilandirma=yapilandirma,
    )

    assert sonuc.islemler == (
        birinci,
    )

    assert sonuc.atlanan_sinyal_sayisi == 1


def test_metrikler_ve_onceki_atlananlar_korunur() -> None:
    birinci = islem_olustur(
        sembol="AAA.IS",
        sinyal_tarihi=date(2026, 1, 1),
        giris_tarihi=date(2026, 1, 2),
        cikis_tarihi=date(2026, 1, 5),
        cikis_fiyati=110.0,
    )

    cakisan = islem_olustur(
        sembol="AAA.IS",
        sinyal_tarihi=date(2026, 1, 2),
        giris_tarihi=date(2026, 1, 3),
        cikis_tarihi=date(2026, 1, 4),
        cikis_fiyati=120.0,
    )

    ikinci = islem_olustur(
        sembol="AAA.IS",
        sinyal_tarihi=date(2026, 1, 5),
        giris_tarihi=date(2026, 1, 6),
        cikis_tarihi=date(2026, 1, 7),
        cikis_fiyati=95.0,
    )

    onceki_atlanan = SkippedSignal(
        sinyal=BacktestSignal(
            sembol="AAA.IS",
            sinyal_tarihi=date(2025, 12, 30),
            skor=40,
            teknik_gorunum=GORUNUM,
        ),
        neden="Sinyal skoru yetersiz.",
    )

    ham_sonuc, yapilandirma = sonuc_olustur(
        islemler=(
            birinci,
            cakisan,
            ikinci,
        ),
        atlananlar=(
            onceki_atlanan,
        ),
    )

    sonuc = cakisan_islemleri_filtrele(
        sonuc=ham_sonuc,
        yapilandirma=yapilandirma,
    )

    assert sonuc.tamamlanan_islem_sayisi == 2
    assert sonuc.atlanan_sinyal_sayisi == 2

    assert sonuc.atlanan_sinyaller[0] is (
        onceki_atlanan
    )

    assert sonuc.metrikler.islem_sayisi == 2

    assert (
        sonuc.metrikler.bitis_sermayesi
        == pytest.approx(104_500.0)
    )

    assert (
        sonuc.metrikler.toplam_net_getiri_orani
        == pytest.approx(0.045)
    )