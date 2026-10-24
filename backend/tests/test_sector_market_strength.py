from __future__ import annotations

import math

import pandas as pd
import pytest

from backend.app.sector_analysis.sector_market_strength import (
    BENCHMARK_SYMBOL,
    SectorIndexDefinition,
    SectorMarketStrengthError,
    analyze_sector_index,
    build_sector_market_map,
    sector_market_rows,
)


def frame(
    start: float,
    daily_step: float,
    *,
    periods: int = 90,
    volume: float = 1_000_000.0,
    end: str = "2026-08-04",
) -> pd.DataFrame:
    index = pd.bdate_range(end=end, periods=periods)
    close = [
        start + daily_step * i
        for i in range(periods)
    ]
    return pd.DataFrame(
        {
            "Open": close,
            "High": [x * 1.01 for x in close],
            "Low": [x * 0.99 for x in close],
            "Close": close,
            "Volume": [volume for _ in close],
        },
        index=index,
    )


def loader_from(mapping):
    def loader(symbol, **kwargs):
        try:
            return mapping[symbol].copy()
        except KeyError as exc:
            raise RuntimeError(f"missing {symbol}") from exc
    return loader


def test_guclu_sektor_xu100e_gore_pozitif_ayrisir():
    benchmark = frame(100.0, 0.20)
    sector = frame(100.0, 0.70)

    result = analyze_sector_index(
        SectorIndexDefinition("TEST", "Test Sektörü", "TEST.IS"),
        benchmark_frame=benchmark,
        loader=loader_from({"TEST.IS": sector}),
    )

    assert result.relative_1d > 0
    assert result.relative_5d > 0
    assert result.relative_20d > 0
    assert result.relative_score == 40
    assert result.trend_status == "Pozitif"
    assert result.strength_score >= 70
    assert result.status == "Güçlü"


def test_zayif_sektor_negatif_goreceli_guc_uretir():
    benchmark = frame(100.0, 0.60)
    sector = frame(150.0, -0.30)

    result = analyze_sector_index(
        SectorIndexDefinition("TEST", "Test Sektörü", "TEST.IS"),
        benchmark_frame=benchmark,
        loader=loader_from({"TEST.IS": sector}),
    )

    assert result.relative_5d < 0
    assert result.relative_20d < 0
    assert result.relative_score == 0
    assert result.trend_status == "Negatif"
    assert result.status in ("Nötr", "Zayıf")


def test_hacim_yoksa_sektor_analizi_yine_devam_eder():
    benchmark = frame(100.0, 0.20)
    sector = frame(100.0, 0.50, volume=0.0)

    result = analyze_sector_index(
        SectorIndexDefinition("TEST", "Test Sektörü", "TEST.IS"),
        benchmark_frame=benchmark,
        loader=loader_from({"TEST.IS": sector}),
    )

    assert result.volume_available is False
    assert result.volume_ratio is None
    assert result.volume_score == 5


def test_sektor_tarihi_xu100den_gerideyse_reddedilir():
    benchmark = frame(100.0, 0.20, end="2026-08-04")
    sector = frame(100.0, 0.50, end="2026-08-03")

    with pytest.raises(
        SectorMarketStrengthError,
        match="Güncel sektör karşılaştırması yapılamadı",
    ):
        analyze_sector_index(
            SectorIndexDefinition("TEST", "Test Sektörü", "TEST.IS"),
            benchmark_frame=benchmark,
            loader=loader_from({"TEST.IS": sector}),
        )


def test_harita_sektorleri_guc_skoruna_gore_siralar():
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.20),
        "FAST.IS": frame(100.0, 0.70),
        "SLOW.IS": frame(120.0, 0.05),
    }
    result = build_sector_market_map(
        sectors=(
            SectorIndexDefinition("SLOW", "Yavaş", "SLOW.IS"),
            SectorIndexDefinition("FAST", "Hızlı", "FAST.IS"),
        ),
        loader=loader_from(mapping),
    )

    assert tuple(item.code for item in result.items) == (
        "FAST",
        "SLOW",
    )
    assert tuple(item.rank for item in result.items) == (1, 2)


def test_tek_sektor_hatasi_tum_haritayi_durdurmaz():
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.20),
        "OK.IS": frame(100.0, 0.50),
    }
    result = build_sector_market_map(
        sectors=(
            SectorIndexDefinition("OK", "Çalışan", "OK.IS"),
            SectorIndexDefinition("BAD", "Eksik", "BAD.IS"),
        ),
        loader=loader_from(mapping),
    )

    assert tuple(item.code for item in result.items) == ("OK",)
    assert len(result.errors) == 1
    assert result.errors[0].startswith("BAD:")


def test_hicbir_sektor_calismiyorsa_acik_hata_verir():
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.20),
    }

    with pytest.raises(
        SectorMarketStrengthError,
        match="Hiçbir sektör endeksi",
    ):
        build_sector_market_map(
            sectors=(
                SectorIndexDefinition("BAD", "Eksik", "BAD.IS"),
            ),
            loader=loader_from(mapping),
        )


def test_dashboard_satirlari_hard_trade_sinyali_uretmez():
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.20),
        "FAST.IS": frame(100.0, 0.70),
    }
    result = build_sector_market_map(
        sectors=(
            SectorIndexDefinition("FAST", "Hızlı", "FAST.IS"),
        ),
        loader=loader_from(mapping),
    )

    row = sector_market_rows(result)[0]

    assert row["Sektör"] == "Hızlı"
    assert row["Endeks"] == "FAST"
    assert "AL" not in row
    assert "SAT" not in row
    assert "Sinyal" not in row
