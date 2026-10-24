from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.app.data.batch_market_data import toplu_fiyat_verisi_getir


def coklu_veri(semboller: list[str], satir: int = 200) -> pd.DataFrame:
    tarihler = pd.date_range("2025-01-01", periods=satir, freq="B")
    sutunlar = pd.MultiIndex.from_product(
        [semboller, ["Open", "High", "Low", "Close", "Volume"]]
    )
    veri = pd.DataFrame(index=tarihler, columns=sutunlar, dtype=float)

    for sira, sembol in enumerate(semboller, start=1):
        taban = np.linspace(100 + sira, 150 + sira, satir)
        veri[(sembol, "Open")] = taban
        veri[(sembol, "High")] = taban + 2
        veri[(sembol, "Low")] = taban - 2
        veri[(sembol, "Close")] = taban + 0.5
        veri[(sembol, "Volume")] = 1_000_000 + sira

    return veri


def test_toplu_veri_indirir_normalize_eder_ve_tekrari_siler() -> None:
    cagrilar: list[list[str]] = []

    def indirici(**kwargs: object) -> pd.DataFrame:
        semboller = list(kwargs["tickers"])  # type: ignore[arg-type]
        cagrilar.append(semboller)
        return coklu_veri(semboller)

    sonuc = toplu_fiyat_verisi_getir(
        ["THYAO", "ASELS.IS", "THYAO"],
        islem_gunu=160,
        parca_boyutu=10,
        indirici=indirici,
    )

    assert cagrilar == [["THYAO.IS", "ASELS.IS"]]
    assert tuple(sonuc.veriler) == ("THYAO.IS", "ASELS.IS")
    assert len(sonuc.veriler["THYAO.IS"]) == 160
    assert list(sonuc.veriler["THYAO.IS"].columns) == [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]
    assert sonuc.hatalar == ()


def test_toplu_veride_eksik_sembol_hata_olarak_korunur() -> None:
    def indirici(**_kwargs: object) -> pd.DataFrame:
        return coklu_veri(["THYAO.IS"])

    sonuc = toplu_fiyat_verisi_getir(
        ["THYAO", "YOK"],
        islem_gunu=160,
        indirici=indirici,
    )

    assert tuple(sonuc.veriler) == ("THYAO.IS",)
    assert sonuc.hatalar[0].sembol == "YOK.IS"
    assert "bulunamadı" in sonuc.hatalar[0].hata


def test_gecersiz_parca_boyutu_reddedilir() -> None:
    with pytest.raises(ValueError, match="Parça boyutu"):
        toplu_fiyat_verisi_getir(["THYAO"], parca_boyutu=0)


def test_guvenli_referans_kaynak_zincirini_korur(tmp_path, monkeypatch) -> None:
    from backend.app.data.batch_market_data import guvenli_referans_fiyat_verisi_getir
    monkeypatch.setattr(
        "backend.app.data.data_source_recovery.gunluk_veri_tazeligini_degerlendir",
        lambda veri: type("F", (), {"kilitli": False})(),
    )
    veri = coklu_veri(["AAA.IS"], satir=10)["AAA.IS"]
    def birincil(**_kwargs):
        raise RuntimeError("ağ yok")
    sonuc = guvenli_referans_fiyat_verisi_getir(
        "AAA",
        islem_gunu=5,
        birincil_indirici=birincil,
        ikincil_yukleyici=lambda _symbol: veri,
        onbellek_klasoru=tmp_path,
    )
    assert "AAA.IS" in sonuc.veriler
    assert sonuc.kaynak_sirasi == ("birincil", "ikincil")
    assert sonuc.kaynak_hatalari



def test_toplu_sorgu_end_tarihine_bugunun_ertesi_gununu_verir() -> None:
    from datetime import date

    kwargs_listesi: list[dict[str, object]] = []

    def indirici(**kwargs: object) -> pd.DataFrame:
        kwargs_listesi.append(dict(kwargs))
        return coklu_veri(list(kwargs["tickers"]))  # type: ignore[arg-type]

    toplu_fiyat_verisi_getir(
        ["THYAO", "ASELS"],
        islem_gunu=160,
        indirme_donemi="1y",
        indirici=indirici,
        bugun=date(2026, 7, 31),
    )

    assert kwargs_listesi[0]["end"] == "2026-08-01"
    assert "period" not in kwargs_listesi[0]


def test_referans_sorgusu_da_end_tarihini_dahil_edecek_sekilde_cagirir() -> None:
    from datetime import date
    from backend.app.data.batch_market_data import (
        referans_fiyat_verisi_getir,
    )

    kwargs_listesi: list[dict[str, object]] = []

    def indirici(**kwargs: object) -> pd.DataFrame:
        kwargs_listesi.append(dict(kwargs))
        return coklu_veri(["THYAO.IS"], satir=20)

    sonuc = referans_fiyat_verisi_getir(
        "THYAO",
        islem_gunu=5,
        indirici=indirici,
        bugun=date(2026, 7, 31),
    )

    assert "THYAO.IS" in sonuc.veriler
    assert kwargs_listesi[0]["end"] == "2026-08-01"
