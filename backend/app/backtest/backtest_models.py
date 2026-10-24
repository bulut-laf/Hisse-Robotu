from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from statistics import mean
from typing import Iterable


CIKIS_SURE_SONU = "Süre Sonu"
CIKIS_ZARAR_DURDUR = "Zarar Durdur"
CIKIS_HEDEF = "Hedef"
CIKIS_VERI_SONU = "Veri Sonu"

GECERLI_CIKIS_NEDENLERI = (
    CIKIS_SURE_SONU,
    CIKIS_ZARAR_DURDUR,
    CIKIS_HEDEF,
    CIKIS_VERI_SONU,
)


@dataclass(frozen=True)
class BacktestConfig:
    """Backtest çalışmasında kullanılacak temel ayarlardır."""

    elde_tutma_gunu: int = 10
    minimum_skor: int = 50
    baslangic_sermayesi: float = 100_000.0
    pozisyon_orani: float = 1.0
    islem_maliyeti_orani: float = 0.001
    zarar_durdur_orani: float | None = None
    hedef_orani: float | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.elde_tutma_gunu <= 30:
            raise ValueError(
                "Elde tutma günü 1 ile 30 arasında olmalıdır."
            )

        if not 0 <= self.minimum_skor <= 100:
            raise ValueError(
                "Minimum skor 0 ile 100 arasında olmalıdır."
            )

        if self.baslangic_sermayesi <= 0:
            raise ValueError(
                "Başlangıç sermayesi pozitif olmalıdır."
            )

        if not 0 < self.pozisyon_orani <= 1:
            raise ValueError(
                "Pozisyon oranı 0'dan büyük ve "
                "1'den küçük veya eşit olmalıdır."
            )

        if not 0 <= self.islem_maliyeti_orani < 0.10:
            raise ValueError(
                "İşlem maliyeti oranı 0 ile 0.10 "
                "arasında olmalıdır."
            )

        self._opsiyonel_orani_dogrula(
            alan_adi="Zarar durdur oranı",
            deger=self.zarar_durdur_orani,
        )

        self._opsiyonel_orani_dogrula(
            alan_adi="Hedef oranı",
            deger=self.hedef_orani,
        )

    @staticmethod
    def _opsiyonel_orani_dogrula(
        alan_adi: str,
        deger: float | None,
    ) -> None:
        if deger is None:
            return

        if not 0 < deger < 1:
            raise ValueError(
                f"{alan_adi} 0 ile 1 arasında olmalıdır."
            )


@dataclass(frozen=True)
class BacktestSignal:
    """Geçmiş bir tarihte üretilmiş teknik analiz sinyalidir."""

    sembol: str
    sinyal_tarihi: date
    skor: int
    teknik_gorunum: str

    def __post_init__(self) -> None:
        temiz_sembol = self.sembol.strip().upper()

        if not temiz_sembol:
            raise ValueError(
                "Sinyal sembolü boş olamaz."
            )

        if not 0 <= self.skor <= 100:
            raise ValueError(
                "Sinyal skoru 0 ile 100 arasında olmalıdır."
            )

        if not self.teknik_gorunum.strip():
            raise ValueError(
                "Teknik görünüm boş olamaz."
            )

        object.__setattr__(
            self,
            "sembol",
            temiz_sembol,
        )


@dataclass(frozen=True)
class BacktestTrade:
    """Backtest sırasında tamamlanmış tek bir işlemdir."""

    sembol: str
    sinyal_tarihi: date
    giris_tarihi: date
    cikis_tarihi: date
    giris_fiyati: float
    cikis_fiyati: float
    skor: int
    teknik_gorunum: str
    brut_getiri_orani: float
    net_getiri_orani: float
    elde_tutulan_bar: int
    cikis_nedeni: str

    def __post_init__(self) -> None:
        temiz_sembol = self.sembol.strip().upper()

        if not temiz_sembol:
            raise ValueError(
                "İşlem sembolü boş olamaz."
            )

        if self.giris_tarihi <= self.sinyal_tarihi:
            raise ValueError(
                "Giriş tarihi sinyal tarihinden sonra olmalıdır."
            )

        if self.cikis_tarihi < self.giris_tarihi:
            raise ValueError(
                "Çıkış tarihi giriş tarihinden önce olamaz."
            )

        if self.giris_fiyati <= 0:
            raise ValueError(
                "Giriş fiyatı pozitif olmalıdır."
            )

        if self.cikis_fiyati <= 0:
            raise ValueError(
                "Çıkış fiyatı pozitif olmalıdır."
            )

        if not 0 <= self.skor <= 100:
            raise ValueError(
                "İşlem skoru 0 ile 100 arasında olmalıdır."
            )

        if self.elde_tutulan_bar <= 0:
            raise ValueError(
                "Elde tutulan bar sayısı pozitif olmalıdır."
            )

        if self.cikis_nedeni not in GECERLI_CIKIS_NEDENLERI:
            raise ValueError(
                f"Geçersiz çıkış nedeni: {self.cikis_nedeni}"
            )

        object.__setattr__(
            self,
            "sembol",
            temiz_sembol,
        )

    @classmethod
    def olustur(
        cls,
        sembol: str,
        sinyal_tarihi: date,
        giris_tarihi: date,
        cikis_tarihi: date,
        giris_fiyati: float,
        cikis_fiyati: float,
        skor: int,
        teknik_gorunum: str,
        elde_tutulan_bar: int,
        cikis_nedeni: str,
        islem_maliyeti_orani: float = 0.0,
    ) -> BacktestTrade:
        """
        Fiyatlardan brüt ve net getiriyi hesaplayarak işlem oluşturur.

        İşlem maliyeti alışta ve satışta ayrı ayrı uygulanır.
        """
        if not 0 <= islem_maliyeti_orani < 0.10:
            raise ValueError(
                "İşlem maliyeti oranı 0 ile 0.10 "
                "arasında olmalıdır."
            )

        if giris_fiyati <= 0:
            raise ValueError(
                "Giriş fiyatı pozitif olmalıdır."
            )

        if cikis_fiyati <= 0:
            raise ValueError(
                "Çıkış fiyatı pozitif olmalıdır."
            )

        brut_getiri = (
            cikis_fiyati / giris_fiyati
        ) - 1

        maliyetli_giris = giris_fiyati * (
            1 + islem_maliyeti_orani
        )

        maliyetli_cikis = cikis_fiyati * (
            1 - islem_maliyeti_orani
        )

        net_getiri = (
            maliyetli_cikis / maliyetli_giris
        ) - 1

        return cls(
            sembol=sembol,
            sinyal_tarihi=sinyal_tarihi,
            giris_tarihi=giris_tarihi,
            cikis_tarihi=cikis_tarihi,
            giris_fiyati=giris_fiyati,
            cikis_fiyati=cikis_fiyati,
            skor=skor,
            teknik_gorunum=teknik_gorunum,
            brut_getiri_orani=brut_getiri,
            net_getiri_orani=net_getiri,
            elde_tutulan_bar=elde_tutulan_bar,
            cikis_nedeni=cikis_nedeni,
        )


@dataclass(frozen=True)
class BacktestMetrics:
    """Tamamlanan işlemlerden hesaplanan performans özetidir."""

    islem_sayisi: int
    kazanan_islem_sayisi: int
    kaybeden_islem_sayisi: int
    basabas_islem_sayisi: int
    kazanma_orani: float
    ortalama_net_getiri_orani: float
    toplam_net_getiri_orani: float
    baslangic_sermayesi: float
    bitis_sermayesi: float
    en_iyi_islem_orani: float | None
    en_kotu_islem_orani: float | None
    kar_faktoru: float | None
    maksimum_ardisik_kayip: int

    @classmethod
    def hesapla(
        cls,
        islemler: Iterable[BacktestTrade],
        yapilandirma: BacktestConfig,
    ) -> BacktestMetrics:
        islem_listesi = tuple(islemler)

        if not islem_listesi:
            return cls(
                islem_sayisi=0,
                kazanan_islem_sayisi=0,
                kaybeden_islem_sayisi=0,
                basabas_islem_sayisi=0,
                kazanma_orani=0.0,
                ortalama_net_getiri_orani=0.0,
                toplam_net_getiri_orani=0.0,
                baslangic_sermayesi=(
                    yapilandirma.baslangic_sermayesi
                ),
                bitis_sermayesi=(
                    yapilandirma.baslangic_sermayesi
                ),
                en_iyi_islem_orani=None,
                en_kotu_islem_orani=None,
                kar_faktoru=None,
                maksimum_ardisik_kayip=0,
            )

        getiriler = tuple(
            islem.net_getiri_orani
            for islem in islem_listesi
        )

        kazananlar = tuple(
            getiri
            for getiri in getiriler
            if getiri > 0
            and not math.isclose(
                getiri,
                0.0,
                abs_tol=1e-12,
            )
        )

        kaybedenler = tuple(
            getiri
            for getiri in getiriler
            if getiri < 0
            and not math.isclose(
                getiri,
                0.0,
                abs_tol=1e-12,
            )
        )

        basabas_sayisi = sum(
            1
            for getiri in getiriler
            if math.isclose(
                getiri,
                0.0,
                abs_tol=1e-12,
            )
        )

        sermaye = yapilandirma.baslangic_sermayesi

        for getiri in getiriler:
            sermaye *= (
                1
                + getiri
                * yapilandirma.pozisyon_orani
            )

        toplam_getiri = (
            sermaye
            / yapilandirma.baslangic_sermayesi
        ) - 1

        toplam_kar = sum(
            kazananlar
        )

        toplam_zarar = abs(
            sum(kaybedenler)
        )

        kar_faktoru = (
            toplam_kar / toplam_zarar
            if toplam_zarar > 0
            else None
        )

        return cls(
            islem_sayisi=len(
                islem_listesi
            ),
            kazanan_islem_sayisi=len(
                kazananlar
            ),
            kaybeden_islem_sayisi=len(
                kaybedenler
            ),
            basabas_islem_sayisi=basabas_sayisi,
            kazanma_orani=(
                len(kazananlar)
                / len(islem_listesi)
            ),
            ortalama_net_getiri_orani=mean(
                getiriler
            ),
            toplam_net_getiri_orani=toplam_getiri,
            baslangic_sermayesi=(
                yapilandirma.baslangic_sermayesi
            ),
            bitis_sermayesi=sermaye,
            en_iyi_islem_orani=max(
                getiriler
            ),
            en_kotu_islem_orani=min(
                getiriler
            ),
            kar_faktoru=kar_faktoru,
            maksimum_ardisik_kayip=(
                _maksimum_ardisik_kayip_hesapla(
                    getiriler
                )
            ),
        )


def _maksimum_ardisik_kayip_hesapla(
    getiriler: Iterable[float],
) -> int:
    maksimum_seri = 0
    mevcut_seri = 0

    for getiri in getiriler:
        if getiri < 0 and not math.isclose(
            getiri,
            0.0,
            abs_tol=1e-12,
        ):
            mevcut_seri += 1
            maksimum_seri = max(
                maksimum_seri,
                mevcut_seri,
            )
        else:
            mevcut_seri = 0

    return maksimum_seri