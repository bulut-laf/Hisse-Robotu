from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..risk.risk_engine import RiskPlan


class SignalEngineError(Exception):
    """Sinyal üretimi sırasında oluşan özel hata."""


@dataclass(frozen=True)
class SignalResult:
    """
    Açıklanabilir kısa vadeli teknik analiz sonucu.
    """

    skor: int
    karar: str

    trend_puani: int
    momentum_puani: int
    hacim_puani: int
    risk_puani: int

    pozitif_nedenler: tuple[str, ...]
    riskler: tuple[str, ...]


def sinyal_uret(
    veri: pd.DataFrame,
    risk_plani: RiskPlan,
) -> SignalResult:
    """
    Teknik göstergeler, hacim ve risk planını kullanarak
    0-100 arasında açıklanabilir sinyal skoru üretir.

    Karar sınıfları:
        Pozitif Teknik Görünüm
        Nötr Teknik Görünüm
        Negatif Teknik Görünüm
    """
    gerekli_sutunlar = {
        "Close",
        "EMA9",
        "EMA21",
        "RSI14",
        "MACD",
        "MACD_Sinyal",
        "MACD_Histogram",
        "Hacim_Orani",
        "Yukselis_Hacim_Patlamasi",
        "Dusus_Hacim_Patlamasi",
        "Gunluk_Getiri_Yuzde",
    }

    eksik_sutunlar = gerekli_sutunlar.difference(
        veri.columns
    )

    if eksik_sutunlar:
        raise SignalEngineError(
            "Sinyal motoru için eksik sütunlar: "
            + ", ".join(sorted(eksik_sutunlar))
        )

    if len(veri) < 2:
        raise SignalEngineError(
            "Sinyal üretmek için en az iki satır veri gereklidir."
        )

    gecerli_veri = veri.dropna(
        subset=list(gerekli_sutunlar)
    )

    if len(gecerli_veri) < 2:
        raise SignalEngineError(
            "Sinyal üretmek için yeterli geçerli veri bulunamadı."
        )

    son = gecerli_veri.iloc[-1]
    onceki = gecerli_veri.iloc[-2]

    pozitif_nedenler: list[str] = []
    riskler: list[str] = []

    trend_puani = _trend_puani_hesapla(
        veri=gecerli_veri,
        pozitif_nedenler=pozitif_nedenler,
        riskler=riskler,
    )

    momentum_puani = _momentum_puani_hesapla(
        son=son,
        onceki=onceki,
        pozitif_nedenler=pozitif_nedenler,
        riskler=riskler,
    )

    hacim_puani = _hacim_puani_hesapla(
        veri=gecerli_veri,
        son=son,
        pozitif_nedenler=pozitif_nedenler,
        riskler=riskler,
    )

    risk_puani = _risk_puani_hesapla(
        risk_plani=risk_plani,
        pozitif_nedenler=pozitif_nedenler,
        riskler=riskler,
    )

    toplam_skor = (
        trend_puani
        + momentum_puani
        + hacim_puani
        + risk_puani
    )

    toplam_skor = int(
        max(0, min(100, toplam_skor))
    )

    karar = _karar_belirle(
        skor=toplam_skor,
        son=son,
        risk_plani=risk_plani,
    )

    return SignalResult(
        skor=toplam_skor,
        karar=karar,
        trend_puani=trend_puani,
        momentum_puani=momentum_puani,
        hacim_puani=hacim_puani,
        risk_puani=risk_puani,
        pozitif_nedenler=tuple(pozitif_nedenler),
        riskler=tuple(riskler),
    )


def _trend_puani_hesapla(
    veri: pd.DataFrame,
    pozitif_nedenler: list[str],
    riskler: list[str],
) -> int:
    """
    Trend yapısını 30 puan üzerinden değerlendirir.
    """
    son = veri.iloc[-1]

    puan = 0

    if son["EMA9"] > son["EMA21"]:
        puan += 15
        pozitif_nedenler.append(
            "EMA9, EMA21 üzerinde."
        )
    else:
        riskler.append(
            "EMA9, EMA21 altında; kısa vadeli trend zayıf."
        )

    if son["Close"] > son["EMA21"]:
        puan += 10
        pozitif_nedenler.append(
            "Kapanış fiyatı EMA21 üzerinde."
        )
    else:
        riskler.append(
            "Kapanış fiyatı EMA21 altında."
        )

    if _son_gunlerde_yukari_ema_kesisimi(
        veri=veri,
        gun_sayisi=3,
    ):
        puan += 5
        pozitif_nedenler.append(
            "Son üç işlem gününde EMA yukarı kesişimi oluştu."
        )

    if _son_gunlerde_asagi_ema_kesisimi(
        veri=veri,
        gun_sayisi=3,
    ):
        riskler.append(
            "Son üç işlem gününde EMA aşağı kesişimi oluştu."
        )

    return min(puan, 30)


def _momentum_puani_hesapla(
    son: pd.Series,
    onceki: pd.Series,
    pozitif_nedenler: list[str],
    riskler: list[str],
) -> int:
    """
    RSI ve MACD momentumunu 30 puan üzerinden değerlendirir.
    """
    puan = 0

    rsi = float(son["RSI14"])

    if 52 <= rsi <= 68:
        puan += 15
        pozitif_nedenler.append(
            "RSI sağlıklı pozitif momentum bölgesinde."
        )

    elif 45 <= rsi < 52:
        puan += 8
        pozitif_nedenler.append(
            "RSI nötr-pozitif bölgede."
        )

    elif 35 <= rsi < 45:
        puan += 4
        riskler.append(
            "RSI zayıf momentum bölgesinde."
        )

    elif 68 < rsi <= 75:
        puan += 7
        riskler.append(
            "RSI güçlü fakat aşırı alıma yaklaşıyor."
        )

    elif rsi > 75:
        riskler.append(
            "RSI aşırı alım bölgesinde."
        )

    elif rsi < 30:
        riskler.append(
            "RSI aşırı satış bölgesinde ve trend zayıf."
        )

    if son["MACD"] > son["MACD_Sinyal"]:
        puan += 10
        pozitif_nedenler.append(
            "MACD, sinyal çizgisinin üzerinde."
        )
    else:
        riskler.append(
            "MACD, sinyal çizgisinin altında."
        )

    if (
        son["MACD_Histogram"]
        > onceki["MACD_Histogram"]
    ):
        puan += 5
        pozitif_nedenler.append(
            "MACD histogramı güçleniyor."
        )
    else:
        riskler.append(
            "MACD histogramı zayıflıyor."
        )

    return min(puan, 30)


def _hacim_puani_hesapla(
    veri: pd.DataFrame,
    son: pd.Series,
    pozitif_nedenler: list[str],
    riskler: list[str],
) -> int:
    """
    Hacim davranışını 20 puan üzerinden değerlendirir.
    """
    puan = 0

    if bool(son["Yukselis_Hacim_Patlamasi"]):
        puan += 15
        pozitif_nedenler.append(
            "Yükseliş, güçlü hacim patlamasıyla destekleniyor."
        )

    elif float(son["Hacim_Orani"]) >= 1.20:
        puan += 8
        pozitif_nedenler.append(
            "Hacim 20 günlük ortalamanın belirgin üzerinde."
        )

    elif float(son["Hacim_Orani"]) >= 1.00:
        puan += 4
        pozitif_nedenler.append(
            "Hacim 20 günlük ortalamanın üzerinde."
        )

    else:
        riskler.append(
            "Hacim 20 günlük ortalamanın altında."
        )

    if bool(son["Dusus_Hacim_Patlamasi"]):
        riskler.append(
            "Düşüş, olağan dışı yüksek hacimle gerçekleşiyor."
        )

    son_bes_gun_yukselis_patlamasi = int(
        veri[
            "Yukselis_Hacim_Patlamasi"
        ].tail(5).sum()
    )

    if son_bes_gun_yukselis_patlamasi >= 2:
        puan += 5
        pozitif_nedenler.append(
            "Son beş günde tekrarlayan yükseliş hacim onayı var."
        )

    return min(puan, 20)


def _risk_puani_hesapla(
    risk_plani: RiskPlan,
    pozitif_nedenler: list[str],
    riskler: list[str],
) -> int:
    """
    Risk/ödül ve volatiliteyi 20 puan üzerinden değerlendirir.
    """
    puan = 0

    if risk_plani.filtreyi_gecti:
        puan += 10
        pozitif_nedenler.append(
            "Risk/ödül oranı minimum koşulu karşılıyor."
        )
    else:
        riskler.append(
            "Risk/ödül oranı minimum koşulu karşılamıyor."
        )

    if risk_plani.risk_notu == "Düşük Volatiliteli":
        puan += 10
        pozitif_nedenler.append(
            "Volatilite düşük seviyede."
        )

    elif risk_plani.risk_notu == "Orta Volatiliteli":
        puan += 6
        pozitif_nedenler.append(
            "Volatilite orta seviyede."
        )

    else:
        puan += 2
        riskler.append(
            "Volatilite yüksek seviyede."
        )

    return min(puan, 20)


def _karar_belirle(
    skor: int,
    son: pd.Series,
    risk_plani: RiskPlan,
) -> str:
    """
    Skor ve kritik teknik koşullara göre karar üretir.
    """
    trend_pozitif = (
        son["EMA9"] > son["EMA21"]
        and son["Close"] > son["EMA21"]
    )

    momentum_pozitif = (
        son["MACD"] > son["MACD_Sinyal"]
    )

    ciddi_hacim_riski = bool(
        son["Dusus_Hacim_Patlamasi"]
    )

    if (
        skor >= 75
        and trend_pozitif
        and momentum_pozitif
        and risk_plani.filtreyi_gecti
        and not ciddi_hacim_riski
        and son["RSI14"] <= 75
    ):
        return "Pozitif Teknik Görünüm"

    if (
        skor <= 35
        or ciddi_hacim_riski
        or (
            son["EMA9"] < son["EMA21"]
            and son["MACD"] < son["MACD_Sinyal"]
        )
    ):
        return "Negatif Teknik Görünüm"

    return "Nötr Teknik Görünüm"


def _son_gunlerde_yukari_ema_kesisimi(
    veri: pd.DataFrame,
    gun_sayisi: int,
) -> bool:
    fark = veri["EMA9"] - veri["EMA21"]

    kesisim = (
        (fark > 0)
        & (fark.shift(1) <= 0)
    )

    return bool(
        kesisim.tail(gun_sayisi).any()
    )


def _son_gunlerde_asagi_ema_kesisimi(
    veri: pd.DataFrame,
    gun_sayisi: int,
) -> bool:
    fark = veri["EMA9"] - veri["EMA21"]

    kesisim = (
        (fark < 0)
        & (fark.shift(1) >= 0)
    )

    return bool(
        kesisim.tail(gun_sayisi).any()
    )