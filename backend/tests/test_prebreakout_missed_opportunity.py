import pytest

from backend.app.prebreakout.prebreakout_missed_opportunity import (
    HistoricalCandidateDecision,
    MissedOpportunityReason,
    filtre_etki_tablosu,
    kacirilan_firsatlari_degerlendir,
    kacirilan_firsatlar_tablosu,
)


def _decision(
    symbol: str,
    *,
    selected: bool = False,
    sessions: int = 20,
    close20: float | None = 5.0,
    max20: float | None = 12.0,
    rejected_by: tuple[str, ...] = ("momentum",),
):
    return HistoricalCandidateDecision(
        symbol=symbol,
        cut_date="2026-07-01",
        selected=selected,
        future_session_count=sessions,
        close_return_20_pct=close20,
        max_return_20_pct=max20,
        rejected_by=rejected_by,
    )


def test_yalniz_secilmeyen_guclu_hareketler_kacirilan_firsat_sayilir():
    result = kacirilan_firsatlari_degerlendir(
        (
            _decision("AAA", max20=15.0),
            _decision("BBB", max20=9.9),
            _decision("CCC", selected=True, max20=30.0),
        ),
        minimum_required_rejected_sample=1,
    )
    assert result.rejected_count == 2
    assert result.complete_rejected_count == 2
    assert result.missed_strong_move_count == 1
    assert result.opportunities[0].symbol == "AAA"


def test_eksik_20_seans_sonuc_oranina_girmez():
    result = kacirilan_firsatlari_degerlendir(
        (
            _decision("AAA", sessions=19, max20=30.0),
            _decision("BBB", sessions=20, max20=12.0),
        ),
        minimum_required_rejected_sample=1,
    )
    assert result.complete_rejected_count == 1
    assert result.missed_strong_move_count == 1
    assert result.missed_opportunity_rate_pct == 100.0


def test_birden_fazla_elenme_nedeni_ayri_ayri_sayilir():
    result = kacirilan_firsatlari_degerlendir(
        (
            _decision("AAA", rejected_by=("momentum", "rsi_slope")),
            _decision("BBB", max20=4.0, rejected_by=("momentum",)),
        ),
        minimum_required_rejected_sample=1,
        too_strict_minimum_missed_count=1,
    )
    rows = {row.reason: row for row in result.reason_rows}
    assert rows[MissedOpportunityReason.MOMENTUM].rejected_count == 2
    assert rows[MissedOpportunityReason.MOMENTUM].missed_strong_move_count == 1
    assert rows[MissedOpportunityReason.RSI_EGIMI].missed_strong_move_count == 1


def test_potansiyel_fazla_sert_filtre_oran_ve_adet_kilidiyle_belirlenir():
    result = kacirilan_firsatlari_degerlendir(
        (
            _decision("A", rejected_by=("momentum",)),
            _decision("B", rejected_by=("momentum",)),
            _decision("C", max20=2.0, rejected_by=("momentum",)),
            _decision("D", max20=2.0, rejected_by=("momentum",)),
        ),
        minimum_required_rejected_sample=1,
        too_strict_missed_rate_pct=40.0,
        too_strict_minimum_missed_count=2,
    )
    row = next(item for item in result.reason_rows if item.reason is MissedOpportunityReason.MOMENTUM)
    assert row.missed_rate_pct == 50.0
    assert row.potentially_too_strict


def test_veri_eksikligi_esik_fazla_sert_olarak_isaretlenmez():
    result = kacirilan_firsatlari_degerlendir(
        (
            _decision("A", rejected_by=("missing_data",)),
            _decision("B", rejected_by=("missing_data",)),
            _decision("C", rejected_by=("missing_data",)),
        ),
        minimum_required_rejected_sample=1,
        too_strict_missed_rate_pct=1.0,
        too_strict_minimum_missed_count=1,
    )
    row = next(item for item in result.reason_rows if item.reason is MissedOpportunityReason.VERI_EKSIK)
    assert not row.potentially_too_strict


def test_bilinmeyen_neden_guvenli_bicimde_raporlanir():
    result = kacirilan_firsatlari_degerlendir(
        (_decision("AAA", rejected_by=()),),
        minimum_required_rejected_sample=1,
        too_strict_minimum_missed_count=1,
    )
    assert result.opportunities[0].primary_reason is MissedOpportunityReason.BILINMIYOR


def test_yetersiz_orneklem_esik_degisikligi_onermez():
    result = kacirilan_firsatlari_degerlendir(
        (_decision("AAA"),),
        minimum_required_rejected_sample=10,
    )
    assert not result.sufficient_sample
    assert "eşik değişikliği için kesin hüküm verilmemeli" in result.note


def test_tablolar_kritik_karar_alanlarini_icerir():
    result = kacirilan_firsatlari_degerlendir(
        (_decision("AAA", rejected_by=("momentum", "macd_hist_slope")),),
        minimum_required_rejected_sample=1,
        too_strict_minimum_missed_count=1,
    )
    opportunities = kacirilan_firsatlar_tablosu(result)
    filters = filtre_etki_tablosu(result)
    assert {"Sembol", "20G en yüksek (%)", "Birincil elenme nedeni"} <= set(opportunities.columns)
    assert {"Filtre", "Kaçırma oranı (%)", "Potansiyel fazla sert"} <= set(filters.columns)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"strong_move_threshold_pct": 0},
        {"minimum_future_sessions": 0},
        {"minimum_required_rejected_sample": 0},
        {"too_strict_missed_rate_pct": -1},
        {"too_strict_missed_rate_pct": 101},
        {"too_strict_minimum_missed_count": 0},
    ],
)
def test_gecersiz_esikler_reddedilir(kwargs):
    with pytest.raises(ValueError):
        kacirilan_firsatlari_degerlendir((), **kwargs)
