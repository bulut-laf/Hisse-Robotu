from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.market_regime import (
    MarketRegimeError,
    POZITIF,
    RISKLI,
    SECICI,
    endeks_sembolunu_hazirla,
    piyasa_rejimini_analiz_et,
)


def _veri(*, direction: str = "up", bars: int = 1300, volume: bool = True) -> pd.DataFrame:
    idx = pd.bdate_range(end=pd.Timestamp.now().normalize() - pd.offsets.BDay(1), periods=bars)
    if direction == "up": close = np.linspace(100, 220, bars) + np.sin(np.arange(bars)/7)
    elif direction == "down": close = np.linspace(220, 100, bars) + np.sin(np.arange(bars)/7)
    else: close = 150 + np.sin(np.arange(bars)/5)*2
    vol = np.linspace(1_000_000, 1_300_000, bars) if volume else np.zeros(bars)
    return pd.DataFrame({"Open":close*0.998,"High":close*1.01,"Low":close*0.99,"Close":close,"Volume":vol},index=idx)


def _downloader_factory(daily: pd.DataFrame, hourly: pd.DataFrame | None = None):
    def downloader(**kwargs):
        if kwargs["interval"] == "1h":
            return pd.DataFrame() if hourly is None else hourly.copy()
        return daily.copy()
    return downloader


def test_endeks_aliaslari_normalize_edilir() -> None:
    assert endeks_sembolunu_hazirla("xu100.is") == "XU100"
    assert endeks_sembolunu_hazirla("xu30") == "XU030"
    assert endeks_sembolunu_hazirla("bisttum") == "XUTUM"


def test_saatlik_veri_olmadan_analiz_devam_eder(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.analysis.market_regime.gunluk_veri_tazeligini_degerlendir", lambda veri: type("F",(),{"kilitli":False,"aciklama":"güncel"})())
    sonuc = piyasa_rejimini_analiz_et("XU100", downloader=_downloader_factory(_veri()))
    assert sonuc.saatlik_kullanilabilir is False
    assert sonuc.saatlik_yon is None
    assert sonuc.rejim in (POZITIF, SECICI, RISKLI)
    assert any("Saatlik veri" in x for x in sonuc.riskler)


def test_yukselen_endeks_pozitif_veya_secici_rejim_uretir(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.analysis.market_regime.gunluk_veri_tazeligini_degerlendir", lambda veri: type("F",(),{"kilitli":False,"aciklama":"güncel"})())
    sonuc = piyasa_rejimini_analiz_et("XU100", downloader=_downloader_factory(_veri(direction="up")), saatlik_veri_dene=False)
    assert sonuc.gunluk_yon == "Pozitif"
    assert sonuc.toplam_skor >= 45
    assert sonuc.rejim in (POZITIF, SECICI)


def test_dusen_endeks_riskli_rejim_uretir(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.analysis.market_regime.gunluk_veri_tazeligini_degerlendir", lambda veri: type("F",(),{"kilitli":False,"aciklama":"güncel"})())
    sonuc = piyasa_rejimini_analiz_et("XU100", downloader=_downloader_factory(_veri(direction="down")), saatlik_veri_dene=False)
    assert sonuc.gunluk_yon == "Negatif"
    assert sonuc.rejim == RISKLI


def test_eski_veri_rejim_uretimini_kilitler(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.analysis.market_regime.gunluk_veri_tazeligini_degerlendir", lambda veri: type("F",(),{"kilitli":True,"aciklama":"Eski veri kilidi"})())
    with pytest.raises(MarketRegimeError, match="Eski veri kilidi"):
        piyasa_rejimini_analiz_et("XU100", downloader=_downloader_factory(_veri()), saatlik_veri_dene=False)


def test_endeks_sonucu_islem_plani_alanlari_icermez(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.analysis.market_regime.gunluk_veri_tazeligini_degerlendir", lambda veri: type("F",(),{"kilitli":False,"aciklama":"güncel"})())
    sonuc = piyasa_rejimini_analiz_et("XU100", downloader=_downloader_factory(_veri()), saatlik_veri_dene=False)
    assert not hasattr(sonuc, "lot_sayisi")
    assert not hasattr(sonuc, "stop_loss")


def test_gunluk_veri_hatasinda_kontrollu_yeniden_deneme_yapilir(monkeypatch) -> None:
    cagri = {"sayi": 0}
    guncel = _veri()

    def downloader(**kwargs):
        if kwargs["interval"] == "1h":
            return pd.DataFrame()
        cagri["sayi"] += 1
        if cagri["sayi"] < 3:
            raise RuntimeError("geçici sağlayıcı hatası")
        return guncel.copy()

    monkeypatch.setattr(
        "backend.app.analysis.market_regime.gunluk_veri_tazeligini_degerlendir",
        lambda veri: type(
            "F",
            (),
            {
                "kilitli": False,
                "aciklama": "güncel",
                "kilit_asamasi": "doğrulandı",
                "sonraki_kontrol_zamani": None,
            },
        )(),
    )
    sonuc = piyasa_rejimini_analiz_et(
        "XU100",
        downloader=downloader,
        saatlik_veri_dene=False,
    )

    assert cagri["sayi"] == 3
    assert sonuc.yeniden_deneme_sayisi == 2
    assert sonuc.veri_kaynagi == "birincil"


def test_birincil_kaynak_tukenince_ikincil_kaynaga_gecilir(monkeypatch) -> None:
    guncel = _veri()

    def birincil(**kwargs):
        raise RuntimeError("birincil kaynak kullanılamıyor")

    def ikincil(**kwargs):
        return guncel.copy()

    monkeypatch.setattr(
        "backend.app.analysis.market_regime.gunluk_veri_tazeligini_degerlendir",
        lambda veri: type(
            "F",
            (),
            {
                "kilitli": False,
                "aciklama": "güncel",
                "kilit_asamasi": "doğrulandı",
                "sonraki_kontrol_zamani": None,
            },
        )(),
    )
    sonuc = piyasa_rejimini_analiz_et(
        "XU100",
        downloader=birincil,
        ikincil_downloader=ikincil,
        saatlik_veri_dene=False,
    )

    assert sonuc.veri_kaynagi == "ikincil"
    assert sonuc.yeniden_deneme_sayisi == 2
