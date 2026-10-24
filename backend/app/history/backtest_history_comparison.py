from __future__ import annotations

from dataclasses import dataclass

from .backtest_history import (
    PORTFOY_ANALIZI,
    TEK_HISSE_ANALIZI,
    BacktestHistoryRecord,
)


YUKSEK_DAHA_IYI = "yuksek"
DUSUK_DAHA_IYI = "dusuk"
NOTR = "notr"
ILK_KAYIT = "ilk"
IKINCI_KAYIT = "ikinci"
ESIT = "esit"


class BacktestHistoryComparisonError(ValueError):
    """İki geçmiş kaydı anlamlı biçimde karşılaştırılamadığında oluşur."""


@dataclass(frozen=True)
class HistoryComparisonMetric:
    """İki geçmiş kaydın tek bir performans ölçütündeki farkı."""

    anahtar: str
    etiket: str
    birim: str
    ilk_deger: float
    ikinci_deger: float
    fark: float
    iyilik_yonu: str
    lider: str


@dataclass(frozen=True)
class BacktestHistoryComparison:
    """İki aynı tür backtest geçmiş kaydının karşılaştırma özeti."""

    ilk: BacktestHistoryRecord
    ikinci: BacktestHistoryRecord
    metrikler: tuple[HistoryComparisonMetric, ...]
    semboller_ayni: bool
    donem_ayni: bool
    veri_ayni: bool
    ayarlar_ayni: bool
    dogrudan_karsilastirilabilir: bool
    uyarilar: tuple[str, ...]

    def metrik(self, anahtar: str) -> HistoryComparisonMetric | None:
        return next(
            (metrik for metrik in self.metrikler if metrik.anahtar == anahtar),
            None,
        )


def gecmis_kayitlarini_karsilastir(
    ilk: BacktestHistoryRecord,
    ikinci: BacktestHistoryRecord,
) -> BacktestHistoryComparison:
    """İki geçmiş kaydı veri uyumu ve performans farklarıyla karşılaştırır."""

    if not isinstance(ilk, BacktestHistoryRecord) or not isinstance(
        ikinci, BacktestHistoryRecord
    ):
        raise TypeError("Karşılaştırma için iki BacktestHistoryRecord gereklidir.")
    if ilk.kayit_kimligi == ikinci.kayit_kimligi:
        raise BacktestHistoryComparisonError(
            "Aynı analiz geçmişi kaydı kendisiyle karşılaştırılamaz."
        )
    if ilk.analiz_turu not in (TEK_HISSE_ANALIZI, PORTFOY_ANALIZI):
        raise BacktestHistoryComparisonError(
            "Güncel teknik analiz kayıtları performans karşılaştırmasına uygun değildir."
        )
    if ilk.analiz_turu != ikinci.analiz_turu:
        raise BacktestHistoryComparisonError(
            "Yalnızca aynı tür analiz geçmişi kayıtları karşılaştırılabilir."
        )

    semboller_ayni = ilk.semboller == ikinci.semboller
    donem_ayni = ilk.donem == ikinci.donem
    veri_ayni = ilk.veri_kimligi == ikinci.veri_kimligi
    ayarlar_ayni = ilk.ayar_kimligi == ikinci.ayar_kimligi
    dogrudan = semboller_ayni and donem_ayni and veri_ayni

    uyarilar: list[str] = []
    if not semboller_ayni:
        uyarilar.append(
            "Sembol kümeleri farklı; performans farkı yalnızca genel karşılaştırmadır."
        )
    if not donem_ayni:
        uyarilar.append(
            "Analiz dönemleri farklı; toplam getiri ve işlem sayısı doğrudan kıyaslanmamalıdır."
        )
    if not veri_ayni:
        uyarilar.append(
            "Veri kimlikleri farklı; sonuç farkında veri güncellemesi veya dönem değişimi etkili olabilir."
        )
    if dogrudan and ayarlar_ayni:
        uyarilar.append(
            "Veri ve ayarlar aynı; kalan küçük farklar kayıt zamanı veya sayısal yuvarlamadan kaynaklanabilir."
        )

    metrikler = _ortak_metrikler(ilk, ikinci)
    if ilk.analiz_turu == TEK_HISSE_ANALIZI:
        metrikler.extend(_tek_hisse_metrikleri(ilk, ikinci))
    elif ilk.analiz_turu == PORTFOY_ANALIZI:
        metrikler.extend(_portfoy_metrikleri(ilk, ikinci))

    return BacktestHistoryComparison(
        ilk=ilk,
        ikinci=ikinci,
        metrikler=tuple(metrikler),
        semboller_ayni=semboller_ayni,
        donem_ayni=donem_ayni,
        veri_ayni=veri_ayni,
        ayarlar_ayni=ayarlar_ayni,
        dogrudan_karsilastirilabilir=dogrudan,
        uyarilar=tuple(uyarilar),
    )


def _ortak_metrikler(
    ilk: BacktestHistoryRecord,
    ikinci: BacktestHistoryRecord,
) -> list[HistoryComparisonMetric]:
    metrikler = [
        _metrik(
            "bitis_sermayesi",
            "Bitiş sermayesi",
            "para",
            ilk.bitis_sermayesi,
            ikinci.bitis_sermayesi,
            YUKSEK_DAHA_IYI,
        ),
        _metrik(
            "toplam_getiri_yuzde",
            "Toplam getiri",
            "yuzde",
            ilk.toplam_getiri_yuzde,
            ikinci.toplam_getiri_yuzde,
            YUKSEK_DAHA_IYI,
        ),
        _metrik(
            "maksimum_dusus_yuzde",
            "Maksimum düşüş",
            "yuzde",
            ilk.maksimum_dusus_yuzde,
            ikinci.maksimum_dusus_yuzde,
            DUSUK_DAHA_IYI,
        ),
        _metrik(
            "guncel_dusus_yuzde",
            "Güncel düşüş",
            "yuzde",
            ilk.guncel_dusus_yuzde,
            ikinci.guncel_dusus_yuzde,
            DUSUK_DAHA_IYI,
        ),
        _metrik(
            "tamamlanan_islem_sayisi",
            "Tamamlanan işlem",
            "sayi",
            float(ilk.tamamlanan_islem_sayisi),
            float(ikinci.tamamlanan_islem_sayisi),
            NOTR,
        ),
        _metrik(
            "atlanan_islem_sayisi",
            "Atlanan işlem/sinyal",
            "sayi",
            float(ilk.atlanan_islem_sayisi),
            float(ikinci.atlanan_islem_sayisi),
            NOTR,
        ),
        _metrik(
            "getiri_dusus_orani",
            "Getiri / maksimum düşüş",
            "oran",
            _getiri_dusus_orani(ilk),
            _getiri_dusus_orani(ikinci),
            YUKSEK_DAHA_IYI,
        ),
    ]
    if ilk.kar_faktoru is not None and ikinci.kar_faktoru is not None:
        metrikler.insert(
            4,
            _metrik(
                "kar_faktoru",
                "Kâr faktörü",
                "oran",
                ilk.kar_faktoru,
                ikinci.kar_faktoru,
                YUKSEK_DAHA_IYI,
            ),
        )
    return metrikler


def _tek_hisse_metrikleri(
    ilk: BacktestHistoryRecord,
    ikinci: BacktestHistoryRecord,
) -> list[HistoryComparisonMetric]:
    if ilk.kazanma_yuzde is None or ikinci.kazanma_yuzde is None:
        return []
    return [
        _metrik(
            "kazanma_yuzde",
            "Kazanma oranı",
            "yuzde",
            ilk.kazanma_yuzde,
            ikinci.kazanma_yuzde,
            YUKSEK_DAHA_IYI,
        )
    ]


def _portfoy_metrikleri(
    ilk: BacktestHistoryRecord,
    ikinci: BacktestHistoryRecord,
) -> list[HistoryComparisonMetric]:
    metrikler: list[HistoryComparisonMetric] = []
    if (
        ilk.ortalama_sermaye_kullanim_yuzde is not None
        and ikinci.ortalama_sermaye_kullanim_yuzde is not None
    ):
        metrikler.append(
            _metrik(
                "ortalama_sermaye_kullanim_yuzde",
                "Ortalama sermaye kullanımı",
                "yuzde",
                ilk.ortalama_sermaye_kullanim_yuzde,
                ikinci.ortalama_sermaye_kullanim_yuzde,
                NOTR,
            )
        )
    if ilk.maksimum_pozisyon is not None and ikinci.maksimum_pozisyon is not None:
        metrikler.append(
            _metrik(
                "maksimum_pozisyon",
                "Maksimum pozisyon",
                "sayi",
                float(ilk.maksimum_pozisyon),
                float(ikinci.maksimum_pozisyon),
                NOTR,
            )
        )
    return metrikler


def _getiri_dusus_orani(kayit: BacktestHistoryRecord) -> float:
    if kayit.maksimum_dusus_yuzde <= 0:
        return 0.0
    return kayit.toplam_getiri_yuzde / kayit.maksimum_dusus_yuzde


def _metrik(
    anahtar: str,
    etiket: str,
    birim: str,
    ilk_deger: float,
    ikinci_deger: float,
    iyilik_yonu: str,
) -> HistoryComparisonMetric:
    fark = ikinci_deger - ilk_deger
    lider = _lider_belirle(ilk_deger, ikinci_deger, iyilik_yonu)
    return HistoryComparisonMetric(
        anahtar=anahtar,
        etiket=etiket,
        birim=birim,
        ilk_deger=ilk_deger,
        ikinci_deger=ikinci_deger,
        fark=fark,
        iyilik_yonu=iyilik_yonu,
        lider=lider,
    )


def _lider_belirle(ilk: float, ikinci: float, iyilik_yonu: str) -> str:
    if abs(ikinci - ilk) < 1e-12 or iyilik_yonu == NOTR:
        return ESIT
    if iyilik_yonu == YUKSEK_DAHA_IYI:
        return IKINCI_KAYIT if ikinci > ilk else ILK_KAYIT
    if iyilik_yonu == DUSUK_DAHA_IYI:
        return IKINCI_KAYIT if ikinci < ilk else ILK_KAYIT
    raise ValueError("Bilinmeyen metrik iyilik yönü.")
