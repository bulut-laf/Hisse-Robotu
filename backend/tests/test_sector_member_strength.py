from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.app.analysis.bist_universe import (
    BistUniverse,
    BistUniverseRepository,
)
from backend.app.sector_analysis.sector_member_strength import (
    BENCHMARK_SYMBOL,
    SectorMemberDefinition,
    SectorMemberStrengthError,
    build_sector_member_strength_map,
    sector_member_strength_rows,
)


CSV = """BILESEN KODU;BULTEN_ADI;ENDEKS KODU;ENDEKS ADI;ENDEKS INGILIZCE ADI;TARIH(GG/AA/YYYY)
CONSTITUENT CODE;CONSTITUENT NAME;INDEX CODE;INDEX NAME IN TURKISH;INDEX NAME IN ENGLISH;DATE(DD/MM/YYYY)
AAA.E;AAA;XU100;BIST 100;BIST 100;04/08/2026
BBB.E;BBB;XU100;BIST 100;BIST 100;04/08/2026
CCC.E;CCC;XU100;BIST 100;BIST 100;04/08/2026
DDD.E;DDD;XU100;BIST 100;BIST 100;04/08/2026
AAA.E;AAA;XTEST;TEST SEKTOR;TEST;04/08/2026
BBB.E;BBB;XTEST;TEST SEKTOR;TEST;04/08/2026
CCC.E;CCC;XTEST;TEST SEKTOR;TEST;04/08/2026
AAA.E;AAA;XFAST;HIZLI;FAST;04/08/2026
BBB.E;BBB;XFAST;HIZLI;FAST;04/08/2026
CCC.E;CCC;XFAST;HIZLI;FAST;04/08/2026
BBB.E;BBB;XSLOW;YAVAS;SLOW;04/08/2026
CCC.E;CCC;XSLOW;YAVAS;SLOW;04/08/2026
DDD.E;DDD;XSLOW;YAVAS;SLOW;04/08/2026
AAA.E;AAA;XTWO;IKI UYELI;TWO;04/08/2026
BBB.E;BBB;XTWO;IKI UYELI;TWO;04/08/2026
AAA.E;AAA;XONE;TEK UYELI;ONE;04/08/2026
"""


def frame(
    start: float,
    step: float,
    *,
    periods: int = 90,
    end: str = "2026-08-04",
    volume: float = 1_000_000.0,
) -> pd.DataFrame:
    idx = pd.bdate_range(end=end, periods=periods)
    close = [start + step * i for i in range(periods)]
    return pd.DataFrame(
        {
            "Open": close,
            "High": [x * 1.01 for x in close],
            "Low": [x * 0.99 for x in close],
            "Close": close,
            "Volume": [volume for _ in close],
        },
        index=idx,
    )


def repository(tmp_path: Path) -> BistUniverseRepository:
    snapshot = tmp_path / "snapshot.csv"
    snapshot.write_text(CSV, encoding="utf-8")
    return BistUniverseRepository(
        snapshot_yolu=snapshot,
        onbellek_yolu=tmp_path / "missing-cache.csv",
        indirici=lambda _url: (_ for _ in ()).throw(OSError("offline")),
    )


def loader_from(mapping, calls=None):
    def loader(symbol, **kwargs):
        if calls is not None:
            calls[symbol] = calls.get(symbol, 0) + 1
        try:
            return mapping[symbol].copy()
        except KeyError as exc:
            raise RuntimeError(f"missing {symbol}") from exc
    return loader


def test_repository_generic_sektor_endeksi_yukler(tmp_path: Path):
    repo = repository(tmp_path)

    sector = repo.endeks_bilesenlerini_yukle(
        "xtest",
        endeks_adi="Test Sektörü",
        internetten_guncelle=False,
    )

    assert sector.endeks_kodu == "XTEST"
    assert sector.ad == "Test Sektörü"
    assert sector.semboller == ("AAA.IS", "BBB.IS", "CCC.IS")


def test_repository_gecersiz_endeks_kodunu_reddeder(tmp_path: Path):
    repo = repository(tmp_path)

    with pytest.raises(ValueError, match="Geçersiz BIST endeks kodu"):
        repo.endeks_bilesenlerini_yukle(
            "X TEST!",
            internetten_guncelle=False,
        )


def test_sektor_bist100_uyeleriyle_kisitlanir(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.7),
        "BBB.IS": frame(100.0, 0.6),
        "CCC.IS": frame(100.0, 0.5),
    }

    result = build_sector_member_strength_map(
        sectors=(SectorMemberDefinition("XTEST", "Test"),),
        repository=repo,
        loader=loader_from(mapping),
        refresh_membership=False,
    )

    item = result.items[0]
    assert item.member_count == 3
    assert item.valid_member_count == 3
    assert item.coverage_ratio == 1.0


def test_guclu_uyeler_pozitif_goreceli_guc_uretir(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.8),
        "BBB.IS": frame(100.0, 0.7),
        "CCC.IS": frame(100.0, 0.6),
    }

    item = build_sector_member_strength_map(
        sectors=(SectorMemberDefinition("XTEST", "Test"),),
        repository=repo,
        loader=loader_from(mapping),
        refresh_membership=False,
    ).items[0]

    assert item.relative_1d > 0
    assert item.relative_5d > 0
    assert item.relative_20d > 0
    assert item.relative_score == 40
    assert item.strength_score >= 70
    assert item.status == "Güçlü"


def test_zayif_uyeler_negatif_goreceli_guc_uretir(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.7),
        "AAA.IS": frame(160.0, -0.20),
        "BBB.IS": frame(170.0, -0.25),
        "CCC.IS": frame(180.0, -0.30),
    }

    item = build_sector_member_strength_map(
        sectors=(SectorMemberDefinition("XTEST", "Test"),),
        repository=repo,
        loader=loader_from(mapping),
        refresh_membership=False,
    ).items[0]

    assert item.relative_5d < 0
    assert item.relative_20d < 0
    assert item.relative_score == 0
    assert item.strength_score < 40
    assert item.status == "Zayıf"


def test_eski_uye_kapsama_hesabinda_guncel_sayilmaz(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.7),
        "BBB.IS": frame(100.0, 0.6),
        "CCC.IS": frame(100.0, 0.5, end="2026-08-03"),
    }

    item = build_sector_member_strength_map(
        sectors=(SectorMemberDefinition("XTEST", "Test"),),
        repository=repo,
        loader=loader_from(mapping),
        minimum_members=2,
        minimum_coverage=0.60,
        refresh_membership=False,
    ).items[0]

    assert item.member_count == 3
    assert item.valid_member_count == 2
    assert item.coverage_ratio == pytest.approx(2 / 3)


def test_yetersiz_kapsama_acik_hata_uretir(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.7),
    }

    with pytest.raises(
        SectorMemberStrengthError,
        match="Hiçbir sektör",
    ):
        build_sector_member_strength_map(
            sectors=(SectorMemberDefinition("XTEST", "Test"),),
            repository=repo,
            loader=loader_from(mapping),
            minimum_members=2,
            minimum_coverage=0.60,
            refresh_membership=False,
        )


def test_harita_guc_skoruna_gore_siralanir(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.9),
        "BBB.IS": frame(100.0, 0.7),
        "CCC.IS": frame(100.0, 0.5),
        "DDD.IS": frame(180.0, -0.2),
    }

    result = build_sector_member_strength_map(
        sectors=(
            SectorMemberDefinition("XSLOW", "Yavaş"),
            SectorMemberDefinition("XFAST", "Hızlı"),
        ),
        repository=repo,
        loader=loader_from(mapping),
        refresh_membership=False,
    )

    assert result.items[0].code == "XFAST"
    assert result.items[0].rank == 1
    assert result.items[1].rank == 2


def test_ortak_uyeler_tek_sefer_indirilir(tmp_path: Path):
    repo = repository(tmp_path)
    calls = {}
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.9),
        "BBB.IS": frame(100.0, 0.7),
        "CCC.IS": frame(100.0, 0.5),
        "DDD.IS": frame(100.0, 0.1),
    }

    build_sector_member_strength_map(
        sectors=(
            SectorMemberDefinition("XFAST", "Hızlı"),
            SectorMemberDefinition("XSLOW", "Yavaş"),
        ),
        repository=repo,
        loader=loader_from(mapping, calls),
        refresh_membership=False,
    )

    assert calls["BBB.IS"] == 1
    assert calls["CCC.IS"] == 1
    assert calls[BENCHMARK_SYMBOL] == 1


def test_dashboard_satirlari_hard_sinyal_uretmez(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.9),
        "BBB.IS": frame(100.0, 0.7),
        "CCC.IS": frame(100.0, 0.5),
    }

    result = build_sector_member_strength_map(
        sectors=(SectorMemberDefinition("XTEST", "Test"),),
        repository=repo,
        loader=loader_from(mapping),
        refresh_membership=False,
    )
    row = sector_member_strength_rows(result)[0]

    assert row["Sektör"] == "Test"
    assert "AL" not in row
    assert "SAT" not in row
    assert "Sinyal" not in row


def test_iki_uyeli_sektor_2de2_guncelse_dusuk_guvenle_kabul_edilir(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.7),
        "BBB.IS": frame(100.0, 0.6),
    }

    item = build_sector_member_strength_map(
        sectors=(SectorMemberDefinition("XTWO", "İki Üyeli"),),
        repository=repo,
        loader=loader_from(mapping),
        refresh_membership=False,
    ).items[0]

    assert item.member_count == 2
    assert item.valid_member_count == 2
    assert item.coverage_ratio == 1.0
    assert item.confidence == "Düşük"


def test_iki_uyeli_sektor_1de2_guncelse_reddedilir(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.7),
        "BBB.IS": frame(100.0, 0.6, end="2026-08-03"),
    }

    with pytest.raises(
        SectorMemberStrengthError,
        match="Hiçbir sektör",
    ):
        build_sector_member_strength_map(
            sectors=(SectorMemberDefinition("XTWO", "İki Üyeli"),),
            repository=repo,
            loader=loader_from(mapping),
            refresh_membership=False,
        )


def test_tek_uyeli_sektor_sektor_temsili_sayilmaz(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.7),
    }

    with pytest.raises(
        SectorMemberStrengthError,
        match="Hiçbir sektör",
    ):
        build_sector_member_strength_map(
            sectors=(SectorMemberDefinition("XONE", "Tek Üyeli"),),
            repository=repo,
            loader=loader_from(mapping),
            refresh_membership=False,
        )


def test_dashboard_satirinda_guven_alani_vardir(tmp_path: Path):
    repo = repository(tmp_path)
    mapping = {
        BENCHMARK_SYMBOL: frame(100.0, 0.2),
        "AAA.IS": frame(100.0, 0.7),
        "BBB.IS": frame(100.0, 0.6),
    }

    result = build_sector_member_strength_map(
        sectors=(SectorMemberDefinition("XTWO", "İki Üyeli"),),
        repository=repo,
        loader=loader_from(mapping),
        refresh_membership=False,
    )
    row = sector_member_strength_rows(result)[0]

    assert row["Güven"] == "Düşük"
