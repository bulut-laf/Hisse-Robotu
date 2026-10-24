from __future__ import annotations

from datetime import date

import pytest

from backend.app.backtest.backtest_models import (
    BacktestTrade,
)
from backend.app.backtest.equity_curve import (
    EquityCurveAnalyzer,
    EquityCurveError,
)


GORUNUM = "Pozitif Teknik Görünüm"


def islem_olustur(
    sinyal_tarihi: date,
    giris_tarihi: date,
    cikis_tarihi: date,
    net_getiri_orani: float,
) -> BacktestTrade:
    giris_fiyati = 100.0
    cikis_fiyati = (
        giris_fiyati
        * (
            1.0
            + net_getiri_orani
        )
    )

    return BacktestTrade.olustur(
        sembol="AAA.IS",
        sinyal_tarihi=sinyal_tarihi,
        giris_tarihi=giris_tarihi,
        cikis_tarihi=cikis_tarihi,
        giris_fiyati=giris_fiyati,
        cikis_fiyati=cikis_fiyati,
        skor=70,
        teknik_gorunum=GORUNUM,
        elde_tutulan_bar=5,
        cikis_nedeni="Süre Sonu",
        islem_maliyeti_orani=0.0,
    )


def test_ozsermaye_noktalari_ve_bilesik_getiri_hesaplanir() -> None:
    islemler = (
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 1),
            giris_tarihi=date(2026, 1, 2),
            cikis_tarihi=date(2026, 1, 5),
            net_getiri_orani=0.10,
        ),
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 6),
            giris_tarihi=date(2026, 1, 7),
            cikis_tarihi=date(2026, 1, 10),
            net_getiri_orani=-0.20,
        ),
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 11),
            giris_tarihi=date(2026, 1, 12),
            cikis_tarihi=date(2026, 1, 20),
            net_getiri_orani=0.10,
        ),
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 21),
            giris_tarihi=date(2026, 1, 22),
            cikis_tarihi=date(2026, 2, 1),
            net_getiri_orani=0.20,
        ),
    )

    rapor = EquityCurveAnalyzer().analiz_et(
        islemler=islemler,
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=1.0,
    )

    assert rapor.islem_sayisi == 4

    assert (
        rapor.noktalar[0].sonraki_sermaye
        == pytest.approx(110_000.0)
    )

    assert (
        rapor.noktalar[1].sonraki_sermaye
        == pytest.approx(88_000.0)
    )

    assert (
        rapor.noktalar[2].sonraki_sermaye
        == pytest.approx(96_800.0)
    )

    assert (
        rapor.bitis_sermayesi
        == pytest.approx(116_160.0)
    )

    assert (
        rapor.toplam_bilesik_getiri_orani
        == pytest.approx(0.1616)
    )


def test_maksimum_dusus_ve_toparlanma_hesaplanir() -> None:
    islemler = (
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 1),
            giris_tarihi=date(2026, 1, 2),
            cikis_tarihi=date(2026, 1, 5),
            net_getiri_orani=0.10,
        ),
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 6),
            giris_tarihi=date(2026, 1, 7),
            cikis_tarihi=date(2026, 1, 10),
            net_getiri_orani=-0.20,
        ),
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 11),
            giris_tarihi=date(2026, 1, 12),
            cikis_tarihi=date(2026, 1, 20),
            net_getiri_orani=0.10,
        ),
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 21),
            giris_tarihi=date(2026, 1, 22),
            cikis_tarihi=date(2026, 2, 1),
            net_getiri_orani=0.20,
        ),
    )

    rapor = EquityCurveAnalyzer().analiz_et(
        islemler=islemler
    )

    assert rapor.dusus_donemi_sayisi == 1

    maksimum = (
        rapor.maksimum_dusus_donemi
    )

    assert maksimum is not None

    assert (
        rapor.maksimum_dusus_orani
        == pytest.approx(0.20)
    )

    assert maksimum.zirve_tarihi == date(
        2026,
        1,
        5,
    )

    assert maksimum.dip_tarihi == date(
        2026,
        1,
        10,
    )

    assert maksimum.toparlanma_tarihi == date(
        2026,
        2,
        1,
    )

    assert (
        maksimum.zirve_sermayesi
        == pytest.approx(110_000.0)
    )

    assert (
        maksimum.dip_sermayesi
        == pytest.approx(88_000.0)
    )

    assert maksimum.zirve_altinda_gun_sayisi == 27
    assert maksimum.toparlandi_mi is True


def test_toparlanmamis_dusus_acik_donem_olarak_kaydedilir() -> None:
    islemler = (
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 1),
            giris_tarihi=date(2026, 1, 2),
            cikis_tarihi=date(2026, 1, 5),
            net_getiri_orani=0.10,
        ),
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 6),
            giris_tarihi=date(2026, 1, 7),
            cikis_tarihi=date(2026, 1, 20),
            net_getiri_orani=-0.10,
        ),
    )

    rapor = EquityCurveAnalyzer().analiz_et(
        islemler=islemler
    )

    maksimum = (
        rapor.maksimum_dusus_donemi
    )

    assert maksimum is not None
    assert maksimum.toparlanma_tarihi is None
    assert maksimum.toparlandi_mi is False

    assert (
        maksimum.dusus_orani
        == pytest.approx(0.10)
    )

    assert maksimum.zirve_tarihi == date(
        2026,
        1,
        5,
    )

    assert maksimum.dip_tarihi == date(
        2026,
        1,
        20,
    )

    assert maksimum.zirve_altinda_gun_sayisi == 15


def test_pozisyon_orani_sermaye_hesabina_uygulanir() -> None:
    islemler = (
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 1),
            giris_tarihi=date(2026, 1, 2),
            cikis_tarihi=date(2026, 1, 5),
            net_getiri_orani=0.20,
        ),
        islem_olustur(
            sinyal_tarihi=date(2026, 1, 6),
            giris_tarihi=date(2026, 1, 7),
            cikis_tarihi=date(2026, 1, 10),
            net_getiri_orani=-0.10,
        ),
    )

    rapor = EquityCurveAnalyzer().analiz_et(
        islemler=islemler,
        baslangic_sermayesi=100_000.0,
        pozisyon_orani=0.50,
    )

    assert (
        rapor.bitis_sermayesi
        == pytest.approx(104_500.0)
    )

    assert (
        rapor.toplam_bilesik_getiri_orani
        == pytest.approx(0.045)
    )

    assert (
        rapor.noktalar[0]
        .uygulanan_getiri_orani
        == pytest.approx(0.10)
    )

    assert (
        rapor.noktalar[1]
        .uygulanan_getiri_orani
        == pytest.approx(-0.05)
    )


def test_bos_islem_listesi_bos_rapor_dondurur() -> None:
    rapor = EquityCurveAnalyzer().analiz_et(
        islemler=(),
        baslangic_sermayesi=100_000.0,
    )

    assert rapor.islem_sayisi == 0
    assert rapor.dusus_donemi_sayisi == 0
    assert rapor.noktalar == ()
    assert rapor.dusus_donemleri == ()
    assert rapor.maksimum_dusus_orani == 0.0
    assert rapor.maksimum_dusus_donemi is None
    assert rapor.en_uzun_dusus_donemi is None
    assert rapor.bitis_sermayesi == 100_000.0
    assert rapor.toplam_bilesik_getiri_orani == 0.0


def test_gecersiz_ayarlar_hata_verir() -> None:
    analizci = EquityCurveAnalyzer()

    with pytest.raises(
        EquityCurveError,
        match="Başlangıç sermayesi",
    ):
        analizci.analiz_et(
            islemler=(),
            baslangic_sermayesi=0.0,
        )

    with pytest.raises(
        EquityCurveError,
        match="Pozisyon oranı",
    ):
        analizci.analiz_et(
            islemler=(),
            pozisyon_orani=0.0,
        )

    with pytest.raises(
        EquityCurveError,
        match="Pozisyon oranı",
    ):
        analizci.analiz_et(
            islemler=(),
            pozisyon_orani=1.10,
        )