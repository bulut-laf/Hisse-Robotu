from __future__ import annotations

from datetime import date

from backend.app.analysis.bist_universe import BistUniverse
from backend.app.sector_analysis.sector_candidate_context import (
    build_candidate_sector_contexts,
)
from backend.app.sector_analysis.sector_member_strength import (
    SectorMemberStrengthMap,
    SectorMemberStrengthResult,
)


def item(
    code: str,
    name: str,
    score: int,
    status: str,
    confidence: str = "Yüksek",
    relative: float = 1.0,
) -> SectorMemberStrengthResult:
    return SectorMemberStrengthResult(
        rank=1,
        code=code,
        name=name,
        analysis_date=date(2026, 8, 4),
        member_count=5,
        valid_member_count=5,
        coverage_ratio=1.0,
        return_1d=1.0,
        return_5d=2.0,
        return_20d=3.0,
        benchmark_return_1d=0.5,
        benchmark_return_5d=1.0,
        benchmark_return_20d=1.5,
        relative_1d=0.5,
        relative_5d=1.0,
        relative_20d=1.5,
        relative_composite=relative,
        positive_1d_ratio=0.8,
        positive_5d_ratio=0.7,
        above_ema21_ratio=0.7,
        short_trend_ratio=0.6,
        momentum_positive_ratio=0.5,
        median_volume_ratio=1.1,
        relative_score=40,
        trend_score=20,
        momentum_score=10,
        participation_score=10,
        strength_score=score,
        status=status,
        confidence=confidence,
    )


class Repo:
    def __init__(self, memberships):
        self.memberships = memberships

    def endeks_bilesenlerini_yukle(
        self,
        endeks_kodu,
        *,
        endeks_adi=None,
        internetten_guncelle=False,
    ):
        return BistUniverse(
            ad=endeks_adi or endeks_kodu,
            endeks_kodu=endeks_kodu,
            semboller=tuple(self.memberships[endeks_kodu]),
            tarih="04/08/2026",
            kaynak="test",
            resmi_kaynaktan_guncel=False,
        )


def strength_map(*items):
    return SectorMemberStrengthMap(
        reference_universe="BIST 100",
        benchmark_symbol="XU100.IS",
        analysis_date=date(2026, 8, 4),
        items=tuple(items),
    )


def test_ozgul_sektor_genis_sektore_tercih_edilir():
    result = build_candidate_sector_contexts(
        ["TUPRS.IS"],
        strength_map=strength_map(
            item("XUSIN", "Sınai", 80, "Güçlü"),
            item("XKMYA", "Kimya Petrol Plastik", 39, "Zayıf"),
        ),
        repository=Repo(
            {
                "XUSIN": ("TUPRS.IS",),
                "XKMYA": ("TUPRS.IS",),
            }
        ),
    )

    context = result.contexts["TUPRS.IS"]
    assert context.sector_code == "XKMYA"
    assert context.sector_score == 39


def test_banka_xbanki_xumala_tercih_eder():
    result = build_candidate_sector_contexts(
        ["GARAN"],
        strength_map=strength_map(
            item("XUMAL", "Mali", 43, "Nötr"),
            item("XBANK", "Bankacılık", 57, "Pozitif"),
        ),
        repository=Repo(
            {
                "XUMAL": ("GARAN.IS",),
                "XBANK": ("GARAN.IS",),
            }
        ),
    )

    assert result.contexts["GARAN.IS"].sector_code == "XBANK"


def test_sektor_durumu_acik_baglam_etiketine_cevrilir():
    result = build_candidate_sector_contexts(
        ["AAA.IS"],
        strength_map=strength_map(
            item("XULAS", "Ulaştırma", 72, "Güçlü", "Orta"),
        ),
        repository=Repo({"XULAS": ("AAA.IS",)}),
    )

    context = result.contexts["AAA.IS"]
    assert context.label == "Güçlü sektör desteği"
    assert context.sector_confidence == "Orta"


def test_sektoru_bulunamayan_aday_elendirilmez_sadece_baglamsiz_kalir():
    result = build_candidate_sector_contexts(
        ["AAA.IS", "BBB.IS"],
        strength_map=strength_map(
            item("XULAS", "Ulaştırma", 68, "Pozitif"),
        ),
        repository=Repo({"XULAS": ("AAA.IS",)}),
    )

    assert "AAA.IS" in result.contexts
    assert "BBB.IS" not in result.contexts


def test_zayif_sektor_baglami_sinyal_uretmez():
    result = build_candidate_sector_contexts(
        ["AAA.IS"],
        strength_map=strength_map(
            item("XKMYA", "Kimya Petrol Plastik", 39, "Zayıf"),
        ),
        repository=Repo({"XKMYA": ("AAA.IS",)}),
    )

    context = result.contexts["AAA.IS"]
    assert context.label == "Zayıf sektör bağlamı"
    assert "AL" not in context.label
    assert "SAT" not in context.label
