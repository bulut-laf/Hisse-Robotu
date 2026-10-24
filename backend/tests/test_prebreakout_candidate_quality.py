from backend.app.prebreakout.prebreakout_candidate_lifecycle import (
    CandidateLifecycleRecord,
    CandidateLifecycleStatus,
)
from backend.app.prebreakout.prebreakout_candidate_quality import (
    aday_kalitesini_degerlendir,
    aday_kalitesi_tablosu,
)
from backend.app.prebreakout.prebreakout_live_performance import (
    LiveHorizonPerformance,
    LivePerformanceLabel,
    LiveSignalPerformance,
)


def _performance(signal_id: str, stage: str, label: LivePerformanceLabel, close20=6.0, max20=12.0):
    complete = label is not LivePerformanceLabel.OLCULEMIYOR
    return LiveSignalPerformance(
        signal_id=signal_id,
        symbol=f"{signal_id}.IS",
        signal_date="2026-07-01",
        signal_stage=stage,
        entry_close=100.0,
        as_of_date="2026-08-01",
        available_session_count=20 if complete else 5,
        label=label,
        horizons=(
            LiveHorizonPerformance(
                horizon=20,
                measured_session_count=20 if complete else 5,
                close_return_pct=close20 if complete else None,
                max_return_pct=max20 if complete else None,
                min_return_pct=-2.0 if complete else None,
                max_drawdown_pct=-3.0 if complete else None,
            ),
        ),
        note="test",
    )


def _lifecycle(signal_id: str, stage: str, status: CandidateLifecycleStatus, sessions: int):
    return CandidateLifecycleRecord(
        signal_id=signal_id,
        symbol=f"{signal_id}.IS",
        signal_date="2026-07-01",
        signal_stage=stage,
        entry_close=100.0,
        status=status,
        status_date="2026-07-04" if status is not CandidateLifecycleStatus.HAZIRLIK else None,
        elapsed_calendar_days=3,
        observed_session_count=sessions,
        last_close=103.0,
        max_return_pct=4.0,
        min_return_pct=-1.0,
        note="test",
    )


def test_erken_tetiklenme_ilk_uc_seansta_ayri_olculur():
    performances = (
        _performance("A", "E2", LivePerformanceLabel.BASARILI),
        _performance("B", "E2", LivePerformanceLabel.SINIRLI_HAREKET),
    )
    lifecycles = (
        _lifecycle("A", "E2", CandidateLifecycleStatus.TETIKLENDI, 2),
        _lifecycle("B", "E2", CandidateLifecycleStatus.TETIKLENDI, 5),
    )
    result = aday_kalitesini_degerlendir(performances, lifecycles, minimum_required_sample=1)
    assert result.triggered_count == 2
    assert result.early_triggered_count == 1
    assert result.early_trigger_rate_pct == 50.0
    assert result.average_trigger_session == 3.5


def test_yanlis_pozitif_yalniz_olculmus_basarisiz_sonuclardan_hesaplanir():
    performances = (
        _performance("A", "E3", LivePerformanceLabel.BASARILI),
        _performance("B", "E3", LivePerformanceLabel.BASARISIZ, close20=-7.0, max20=2.0),
        _performance("C", "E3", LivePerformanceLabel.OLCULEMIYOR),
    )
    result = aday_kalitesini_degerlendir(performances, (), minimum_required_sample=1)
    assert result.measured_count == 2
    assert result.false_positive_count == 1
    assert result.false_positive_rate_pct == 50.0
    assert result.success_rate_pct == 50.0


def test_e2_e3_e4_asama_bazinda_ayri_raporlanir():
    performances = (
        _performance("A", "E2", LivePerformanceLabel.BASARILI),
        _performance("B", "E3", LivePerformanceLabel.BASARISIZ),
        _performance("C", "E4", LivePerformanceLabel.SINIRLI_HAREKET),
    )
    result = aday_kalitesini_degerlendir(performances, (), minimum_required_sample=1)
    rows = {row.stage: row for row in result.stage_rows}
    assert set(rows) == {"E2", "E3", "E4"}
    assert rows["E2"].success_rate_pct == 100.0
    assert rows["E3"].false_positive_rate_pct == 100.0
    assert rows["E4"].limited_count == 1


def test_20_gunluk_ortalama_getiri_ve_tepe_hareketi_hesaplanir():
    performances = (
        _performance("A", "E4", LivePerformanceLabel.BASARILI, close20=6.0, max20=12.0),
        _performance("B", "E4", LivePerformanceLabel.BASARILI, close20=10.0, max20=18.0),
    )
    result = aday_kalitesini_degerlendir(performances, (), minimum_required_sample=1)
    row = next(item for item in result.stage_rows if item.stage == "E4")
    assert row.average_close_return_20_pct == 8.0
    assert row.average_max_return_20_pct == 15.0


def test_yetersiz_orneklem_kesin_hukum_uretmez():
    result = aday_kalitesini_degerlendir(
        (_performance("A", "E2", LivePerformanceLabel.BASARILI),),
        (),
        minimum_required_sample=10,
    )
    assert not result.sufficient_sample
    assert "kesin kalite hükmü verilmemeli" in result.note


def test_e2_e4_disindaki_asamalar_kalite_raporuna_girmez():
    performances = (
        _performance("A", "E1", LivePerformanceLabel.BASARILI),
        _performance("B", "E2", LivePerformanceLabel.BASARILI),
    )
    result = aday_kalitesini_degerlendir(performances, (), minimum_required_sample=1)
    assert result.total_signal_count == 1
    assert result.measured_count == 1


def test_gecersiz_esikler_reddedilir():
    try:
        aday_kalitesini_degerlendir((), (), minimum_required_sample=0)
    except ValueError:
        pass
    else:
        raise AssertionError("minimum_required_sample=0 reddedilmeliydi")

    try:
        aday_kalitesini_degerlendir((), (), early_trigger_session_limit=0)
    except ValueError:
        pass
    else:
        raise AssertionError("early_trigger_session_limit=0 reddedilmeliydi")


def test_kalite_tablosu_karar_metriklerini_icerir():
    result = aday_kalitesini_degerlendir(
        (_performance("A", "E2", LivePerformanceLabel.BASARILI),),
        (_lifecycle("A", "E2", CandidateLifecycleStatus.TETIKLENDI, 2),),
        minimum_required_sample=1,
    )
    table = aday_kalitesi_tablosu(result)
    assert {"Aşama", "Erken tetiklenme (%)", "Yanlış pozitif (%)", "Ort. 20G kapanış (%)"} <= set(table.columns)
