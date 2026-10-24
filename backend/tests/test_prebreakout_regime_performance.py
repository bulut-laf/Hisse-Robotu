import pytest

from backend.app.prebreakout.prebreakout_regime_performance import (
    MarketRegime,
    RegimeCandidateResult,
    piyasa_rejimine_gore_performansi_degerlendir,
    rejim_ozet_tablosu,
    rejim_performans_tablosu,
)


def _r(
    symbol: str,
    regime: str,
    stage: str,
    *,
    sessions: int = 20,
    close20: float | None = 8.0,
    max20: float | None = 12.0,
    label: str | None = None,
):
    return RegimeCandidateResult(
        symbol=symbol,
        signal_date="2026-07-01",
        stage=stage,
        market_regime=regime,
        future_session_count=sessions,
        close_return_20_pct=close20,
        max_return_20_pct=max20,
        outcome_label=label,
    )


def test_e2_e4_rejim_bazinda_ayri_gruplanir():
    report = piyasa_rejimine_gore_performansi_degerlendir(
        (_r("A", "yükselen", "E2"), _r("B", "yatay", "E3"), _r("C", "zayıf", "E4")),
        minimum_sample_per_group=1,
    )
    keys = {(row.market_regime, row.stage) for row in report.rows}
    assert (MarketRegime.YUKSELEN, "E2") in keys
    assert (MarketRegime.YATAY, "E3") in keys
    assert (MarketRegime.ZAYIF, "E4") in keys


def test_eksik_20_seans_basari_oranina_girmez():
    report = piyasa_rejimine_gore_performansi_degerlendir(
        (_r("A", "yükselen", "E2", sessions=19, max20=30.0), _r("B", "yükselen", "E2")),
        minimum_sample_per_group=1,
    )
    row = report.rows[0]
    assert report.complete_count == 1
    assert row.sample_count == 1
    assert row.success_rate_pct == 100.0


def test_negatif_kapanisli_kisa_sureli_yukselis_sinirli_hareket_sayilir():
    report = piyasa_rejimine_gore_performansi_degerlendir(
        (_r("THYAO", "yatay", "E3", close20=-2.0, max20=13.0),),
        minimum_sample_per_group=1,
    )
    row = report.rows[0]
    assert row.successful_count == 0
    assert row.limited_count == 1


def test_olumlu_kontrol_basariya_girer():
    report = piyasa_rejimine_gore_performansi_degerlendir(
        (_r("TUPRS", "yükselen", "E3", close20=11.0, max20=16.0),),
        minimum_sample_per_group=1,
    )
    assert report.rows[0].successful_count == 1


def test_yetersiz_orneklem_lider_ilani_yapmaz():
    report = piyasa_rejimine_gore_performansi_degerlendir(
        (_r("A", "yükselen", "E4"),),
        minimum_sample_per_group=3,
    )
    assert report.best_reliable_regime is None
    assert report.best_reliable_stage is None
    assert "kesin hüküm verilmemeli" in report.note


def test_yeterli_orneklemde_en_guclu_grup_lider_olur():
    report = piyasa_rejimine_gore_performansi_degerlendir(
        (
            _r("A", "yükselen", "E3", close20=10, max20=15),
            _r("B", "yükselen", "E3", close20=9, max20=14),
            _r("C", "yatay", "E3", close20=-1, max20=5),
            _r("D", "yatay", "E3", close20=1, max20=6),
        ),
        minimum_sample_per_group=2,
    )
    assert report.best_reliable_regime is MarketRegime.YUKSELEN
    assert report.best_reliable_stage == "E3"


def test_bilinmeyen_rejim_guvenli_bicimde_raporlanir_ama_lider_olmaz():
    report = piyasa_rejimine_gore_performansi_degerlendir(
        (_r("A", "???", "E4"), _r("B", "???", "E4")),
        minimum_sample_per_group=1,
    )
    assert report.rows[0].market_regime is MarketRegime.BILINMIYOR
    assert report.best_reliable_regime is None


def test_e0_e1_grup_karsilastirmasina_alinmaz():
    report = piyasa_rejimine_gore_performansi_degerlendir(
        (_r("A", "yükselen", "E1"), _r("B", "yükselen", "E2")),
        minimum_sample_per_group=1,
    )
    assert report.complete_count == 1
    assert all(row.stage in {"E2", "E3", "E4"} for row in report.rows)


def test_tablolar_karar_alanlarini_icerir():
    report = piyasa_rejimine_gore_performansi_degerlendir(
        (_r("A", "yükselen", "E2"),),
        minimum_sample_per_group=1,
    )
    detail = rejim_performans_tablosu(report)
    summary = rejim_ozet_tablosu(report)
    assert {"Piyasa rejimi", "Aşama", "Başarı oranı (%)", "Örneklem yeterli"} <= set(detail.columns)
    assert {"Piyasa rejimi", "Toplam örneklem", "Başarı oranı (%)"} <= set(summary.columns)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"minimum_future_sessions": 0},
        {"minimum_sample_per_group": 0},
        {"success_threshold_pct": 0},
    ],
)
def test_gecersiz_esikler_reddedilir(kwargs):
    with pytest.raises(ValueError):
        piyasa_rejimine_gore_performansi_degerlendir((), **kwargs)
