from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import pandas as pd

from .backtest_models import (
    BacktestConfig,
    BacktestMetrics,
    BacktestSignal,
    BacktestTrade,
    CIKIS_HEDEF,
    CIKIS_SURE_SONU,
    CIKIS_VERI_SONU,
    CIKIS_ZARAR_DURDUR,
)


GEREKLI_FIYAT_SUTUNLARI = (
    "Open",
    "High",
    "Low",
    "Close",
)


class BacktestEngineError(Exception):
    """Backtest motorunda oluşan veri veya çalışma hatası."""


@dataclass(frozen=True)
class SkippedSignal:
    """İşleme dönüştürülemeyen sinyal ve atlanma nedenidir."""

    sinyal: BacktestSignal
    neden: str


@dataclass(frozen=True)
class BacktestResult:
    """Backtest işlemleri, atlanan sinyaller ve metriklerdir."""

    islemler: tuple[BacktestTrade, ...]
    atlanan_sinyaller: tuple[SkippedSignal, ...]
    metrikler: BacktestMetrics

    @property
    def tamamlanan_islem_sayisi(self) -> int:
        return len(self.islemler)

    @property
    def atlanan_sinyal_sayisi(self) -> int:
        return len(self.atlanan_sinyaller)

    @property
    def toplam_sinyal_sayisi(self) -> int:
        return (
            self.tamamlanan_islem_sayisi
            + self.atlanan_sinyal_sayisi
        )


class BacktestEngine:
    """
    Geçmiş fiyat verileri ve önceden üretilmiş sinyaller
    üzerinde işlem simülasyonu gerçekleştirir.

    Her sinyal bağımsız bir işlem olarak değerlendirilir.
    Giriş, sinyal tarihinden sonraki ilk işlem gününün
    açılış fiyatından yapılır.
    """

    def calistir(
        self,
        veriler: Mapping[str, pd.DataFrame],
        sinyaller: Iterable[BacktestSignal],
        yapilandirma: BacktestConfig,
    ) -> BacktestResult:
        hazir_veriler = self._verileri_hazirla(
            veriler
        )

        sirali_sinyaller = sorted(
            tuple(sinyaller),
            key=lambda sinyal: (
                sinyal.sinyal_tarihi,
                sinyal.sembol,
            ),
        )

        islemler: list[BacktestTrade] = []
        atlananlar: list[SkippedSignal] = []

        for sinyal in sirali_sinyaller:
            if (
                sinyal.skor
                < yapilandirma.minimum_skor
            ):
                atlananlar.append(
                    SkippedSignal(
                        sinyal=sinyal,
                        neden=(
                            f"Sinyal skoru {sinyal.skor}; "
                            f"minimum "
                            f"{yapilandirma.minimum_skor} gerekli."
                        ),
                    )
                )
                continue

            fiyat_verisi = hazir_veriler.get(
                sinyal.sembol
            )

            if fiyat_verisi is None:
                atlananlar.append(
                    SkippedSignal(
                        sinyal=sinyal,
                        neden=(
                            "Sembol için fiyat verisi "
                            "bulunamadı."
                        ),
                    )
                )
                continue

            islem, atlanma_nedeni = (
                self._sinyali_isleme_donustur(
                    fiyat_verisi=fiyat_verisi,
                    sinyal=sinyal,
                    yapilandirma=yapilandirma,
                )
            )

            if islem is None:
                atlananlar.append(
                    SkippedSignal(
                        sinyal=sinyal,
                        neden=(
                            atlanma_nedeni
                            or "Sinyal işleme dönüştürülemedi."
                        ),
                    )
                )
                continue

            islemler.append(islem)

        islem_tuple = tuple(islemler)

        metrikler = BacktestMetrics.hesapla(
            islemler=islem_tuple,
            yapilandirma=yapilandirma,
        )

        return BacktestResult(
            islemler=islem_tuple,
            atlanan_sinyaller=tuple(
                atlananlar
            ),
            metrikler=metrikler,
        )

    def _verileri_hazirla(
        self,
        veriler: Mapping[str, pd.DataFrame],
    ) -> dict[str, pd.DataFrame]:
        hazir_veriler: dict[str, pd.DataFrame] = {}

        for ham_sembol, ham_veri in veriler.items():
            sembol = str(
                ham_sembol
            ).strip().upper()

            if not sembol:
                raise BacktestEngineError(
                    "Fiyat verisi sembolü boş olamaz."
                )

            if not isinstance(
                ham_veri,
                pd.DataFrame,
            ):
                raise BacktestEngineError(
                    f"{sembol} fiyat verisi "
                    "pandas DataFrame olmalıdır."
                )

            veri = self._tek_veriyi_hazirla(
                sembol=sembol,
                veri=ham_veri,
            )

            hazir_veriler[sembol] = veri

        return hazir_veriler

    def _tek_veriyi_hazirla(
        self,
        sembol: str,
        veri: pd.DataFrame,
    ) -> pd.DataFrame:
        eksik_sutunlar = [
            sutun
            for sutun in GEREKLI_FIYAT_SUTUNLARI
            if sutun not in veri.columns
        ]

        if eksik_sutunlar:
            raise BacktestEngineError(
                f"{sembol} fiyat verisinde eksik "
                "sütunlar var: "
                + ", ".join(eksik_sutunlar)
            )

        sonuc = veri.loc[
            :,
            list(GEREKLI_FIYAT_SUTUNLARI),
        ].copy()

        tarihler = pd.to_datetime(
            sonuc.index,
            errors="coerce",
        )

        if tarihler.isna().any():
            raise BacktestEngineError(
                f"{sembol} fiyat verisinde "
                "geçersiz tarihler var."
            )

        if tarihler.tz is not None:
            tarihler = tarihler.tz_localize(
                None
            )

        sonuc.index = tarihler.normalize()
        sonuc.index.name = "Date"

        sonuc = sonuc.sort_index()

        if sonuc.index.has_duplicates:
            raise BacktestEngineError(
                f"{sembol} fiyat verisinde "
                "tekrarlanan tarihler var."
            )

        for sutun in GEREKLI_FIYAT_SUTUNLARI:
            sonuc[sutun] = pd.to_numeric(
                sonuc[sutun],
                errors="coerce",
            )

        if sonuc.isna().any().any():
            raise BacktestEngineError(
                f"{sembol} fiyat verisinde "
                "boş veya sayısal olmayan değerler var."
            )

        if (
            sonuc.loc[
                :,
                list(GEREKLI_FIYAT_SUTUNLARI),
            ]
            <= 0
        ).any().any():
            raise BacktestEngineError(
                f"{sembol} fiyat değerleri "
                "pozitif olmalıdır."
            )

        if (
            sonuc["High"] < sonuc["Low"]
        ).any():
            raise BacktestEngineError(
                f"{sembol} verisinde en yüksek fiyat, "
                "en düşük fiyattan küçük olamaz."
            )

        if (
            sonuc["High"] < sonuc["Open"]
        ).any() or (
            sonuc["High"] < sonuc["Close"]
        ).any():
            raise BacktestEngineError(
                f"{sembol} verisinde en yüksek fiyat "
                "açılış veya kapanıştan küçük olamaz."
            )

        if (
            sonuc["Low"] > sonuc["Open"]
        ).any() or (
            sonuc["Low"] > sonuc["Close"]
        ).any():
            raise BacktestEngineError(
                f"{sembol} verisinde en düşük fiyat "
                "açılış veya kapanıştan büyük olamaz."
            )

        return sonuc

    def _sinyali_isleme_donustur(
        self,
        fiyat_verisi: pd.DataFrame,
        sinyal: BacktestSignal,
        yapilandirma: BacktestConfig,
    ) -> tuple[BacktestTrade | None, str | None]:
        sinyal_tarihi = pd.Timestamp(
            sinyal.sinyal_tarihi
        ).normalize()

        if sinyal_tarihi not in fiyat_verisi.index:
            return (
                None,
                "Sinyal tarihi fiyat verisinde bulunamadı.",
            )

        sinyal_konumu = fiyat_verisi.index.get_loc(
            sinyal_tarihi
        )

        if not isinstance(
            sinyal_konumu,
            int,
        ):
            return (
                None,
                "Sinyal tarihi tekil olarak bulunamadı.",
            )

        giris_konumu = sinyal_konumu + 1

        if giris_konumu >= len(
            fiyat_verisi
        ):
            return (
                None,
                "Sinyal tarihinden sonra giriş "
                "yapılabilecek fiyat verisi yok.",
            )

        giris_satiri = fiyat_verisi.iloc[
            giris_konumu
        ]

        giris_fiyati = float(
            giris_satiri["Open"]
        )

        zarar_durdur_fiyati = (
            giris_fiyati
            * (
                1
                - yapilandirma.zarar_durdur_orani
            )
            if (
                yapilandirma.zarar_durdur_orani
                is not None
            )
            else None
        )

        hedef_fiyati = (
            giris_fiyati
            * (
                1
                + yapilandirma.hedef_orani
            )
            if yapilandirma.hedef_orani is not None
            else None
        )

        son_konum = min(
            giris_konumu
            + yapilandirma.elde_tutma_gunu
            - 1,
            len(fiyat_verisi) - 1,
        )

        cikis_konumu: int | None = None
        cikis_fiyati: float | None = None
        cikis_nedeni: str | None = None

        for konum in range(
            giris_konumu,
            son_konum + 1,
        ):
            satir = fiyat_verisi.iloc[
                konum
            ]

            en_yuksek = float(
                satir["High"]
            )

            en_dusuk = float(
                satir["Low"]
            )

            stopa_dokundu = (
                zarar_durdur_fiyati is not None
                and en_dusuk
                <= zarar_durdur_fiyati
            )

            hedefe_dokundu = (
                hedef_fiyati is not None
                and en_yuksek
                >= hedef_fiyati
            )

            if stopa_dokundu:
                cikis_konumu = konum
                cikis_fiyati = (
                    zarar_durdur_fiyati
                )
                cikis_nedeni = (
                    CIKIS_ZARAR_DURDUR
                )
                break

            if hedefe_dokundu:
                cikis_konumu = konum
                cikis_fiyati = hedef_fiyati
                cikis_nedeni = CIKIS_HEDEF
                break

        if cikis_konumu is None:
            cikis_konumu = son_konum

            cikis_fiyati = float(
                fiyat_verisi.iloc[
                    cikis_konumu
                ]["Close"]
            )

            kullanilabilir_bar_sayisi = (
                len(fiyat_verisi)
                - giris_konumu
            )

            cikis_nedeni = (
                CIKIS_VERI_SONU
                if (
                    kullanilabilir_bar_sayisi
                    < yapilandirma.elde_tutma_gunu
                )
                else CIKIS_SURE_SONU
            )

        giris_tarihi = (
            fiyat_verisi.index[
                giris_konumu
            ].date()
        )

        cikis_tarihi = (
            fiyat_verisi.index[
                cikis_konumu
            ].date()
        )

        elde_tutulan_bar = (
            cikis_konumu
            - giris_konumu
            + 1
        )

        islem = BacktestTrade.olustur(
            sembol=sinyal.sembol,
            sinyal_tarihi=sinyal.sinyal_tarihi,
            giris_tarihi=giris_tarihi,
            cikis_tarihi=cikis_tarihi,
            giris_fiyati=giris_fiyati,
            cikis_fiyati=cikis_fiyati,
            skor=sinyal.skor,
            teknik_gorunum=(
                sinyal.teknik_gorunum
            ),
            elde_tutulan_bar=elde_tutulan_bar,
            cikis_nedeni=cikis_nedeni,
            islem_maliyeti_orani=(
                yapilandirma.islem_maliyeti_orani
            ),
        )

        return islem, None