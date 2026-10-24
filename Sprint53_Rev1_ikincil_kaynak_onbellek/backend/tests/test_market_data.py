from __future__ import annotations

import pandas as pd
import pytest

from backend.app.data.market_data import (
    _sutunlari_duzelt,
)


def test_ohlc_araligi_acilis_ve_kapanisi_kapsayacak_sekilde_duzeltilir() -> None:
    veri = pd.DataFrame(
        {
            "Open": [101.0, 100.0],
            "High": [100.5, 102.0],
            "Low": [99.0, 100.5],
            "Close": [100.0, 101.0],
            "Volume": [1_000.0, 2_000.0],
        },
        index=pd.to_datetime(
            [
                "2026-01-02",
                "2026-01-05",
            ]
        ),
    )

    sonuc = _sutunlari_duzelt(veri)

    assert sonuc.loc[
        pd.Timestamp("2026-01-02"),
        "High",
    ] == pytest.approx(101.0)

    assert sonuc.loc[
        pd.Timestamp("2026-01-05"),
        "Low",
    ] == pytest.approx(100.0)

    assert (
        sonuc["High"] >= sonuc["Open"]
    ).all()
    assert (
        sonuc["High"] >= sonuc["Close"]
    ).all()
    assert (
        sonuc["Low"] <= sonuc["Open"]
    ).all()
    assert (
        sonuc["Low"] <= sonuc["Close"]
    ).all()


def test_ohlc_duzeltmesi_gecerli_mumu_degistirmez() -> None:
    veri = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [105.0],
            "Low": [95.0],
            "Close": [102.0],
            "Volume": [1_000.0],
        },
        index=pd.to_datetime(
            ["2026-01-02"]
        ),
    )

    sonuc = _sutunlari_duzelt(veri)

    assert sonuc.iloc[0]["Open"] == pytest.approx(100.0)
    assert sonuc.iloc[0]["High"] == pytest.approx(105.0)
    assert sonuc.iloc[0]["Low"] == pytest.approx(95.0)
    assert sonuc.iloc[0]["Close"] == pytest.approx(102.0)
    assert sonuc.iloc[0]["Volume"] == pytest.approx(1_000.0)


def test_acilis_degeri_eksik_satir_analizden_cikarilir() -> None:
    veri = pd.DataFrame(
        {
            "Open": [float("nan"), 100.0],
            "High": [101.0, 102.0],
            "Low": [99.0, 98.0],
            "Close": [100.5, 101.0],
            "Volume": [1_000.0, 2_000.0],
        },
        index=pd.to_datetime(
            [
                "2026-01-02",
                "2026-01-05",
            ]
        ),
    )

    sonuc = _sutunlari_duzelt(veri)

    assert len(sonuc) == 1
    assert sonuc.index[0] == pd.Timestamp("2026-01-05")


def test_guvenli_kaynak_birincil_basarisizsa_ikincili_kullanir(tmp_path, monkeypatch) -> None:
    from backend.app.data.data_source_recovery import recover_daily_market_data
    monkeypatch.setattr(
        "backend.app.data.data_source_recovery.gunluk_veri_tazeligini_degerlendir",
        lambda veri: type("F", (), {"kilitli": False})(),
    )
    veri = pd.DataFrame(
        {"Open":[100.0],"High":[101.0],"Low":[99.0],"Close":[100.5],"Volume":[1000.0]},
        index=pd.to_datetime(["2026-01-02"]),
    )
    sonuc = recover_daily_market_data(
        "AAA.IS",
        primary_loader=lambda: (_ for _ in ()).throw(RuntimeError("birincil hata")),
        secondary_loader=lambda _symbol: veri,
        cache_root=tmp_path,
    )
    assert sonuc.kaynak == "ikincil"
    assert sonuc.kaynak_sirasi == ("birincil", "ikincil")
    assert "birincil hata" in sonuc.kaynak_hatalari[0]
