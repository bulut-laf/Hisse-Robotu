from backend.app.prebreakout.prebreakout_real_result_evaluation import gercek_sonuclari_degerlendir
from backend.app.prebreakout.prebreakout_live_performance import LiveHorizonPerformance, LivePerformanceLabel, LiveSignalPerformance
from backend.app.prebreakout.prebreakout_candidate_lifecycle import CandidateLifecycleRecord, CandidateLifecycleStatus
from backend.app.prebreakout.prebreakout_paper_portfolio import PaperTrade, PaperTradeStatus


def _perf(i, stage, label, ret=6.0):
    return LiveSignalPerformance(str(i), f"X{i}.IS", "2026-01-01", stage, 100.0, "2026-02-01", 20, label, (LiveHorizonPerformance(20,20,ret,12.0,-2.0,-3.0),), "")

def _life(i, stage, status, sessions=3):
    return CandidateLifecycleRecord(str(i), f"X{i}.IS", "2026-01-01", stage, 100.0, status, "2026-01-05", 4, sessions, 103.0, 4.0, -1.0, "")

def _trade(i, stage, status, pnl):
    return PaperTrade(str(i), f"X{i}.IS", "2026-01-01", stage, status, 100,95,110,10,1000,50,"2026-01-10",110,5,pnl,2,pnl,pnl/10,"")

def test_asama_bazinda_basari_ve_tetiklenme_hesaplanir():
    r=gercek_sonuclari_degerlendir(
        [_perf(1,"E2",LivePerformanceLabel.BASARILI), _perf(2,"E2",LivePerformanceLabel.BASARISIZ,-6)],
        [_life(1,"E2",CandidateLifecycleStatus.TETIKLENDI,2), _life(2,"E2",CandidateLifecycleStatus.BASARISIZ,1)],
        [_trade(1,"E2",PaperTradeStatus.HEDEF,80), _trade(2,"E2",PaperTradeStatus.STOP,-60)],
        minimum_required_sample=2,
    )
    e2=r.stage_rows[0]
    assert r.sufficient_sample is True
    assert e2.success_rate_pct == 50.0
    assert e2.trigger_rate_pct == 50.0
    assert e2.average_trigger_session == 2.0

def test_kucuk_orneklem_kesin_hukum_uretmez():
    r=gercek_sonuclari_degerlendir([_perf(1,"E3",LivePerformanceLabel.BASARILI)], [], [], minimum_required_sample=10)
    assert r.sufficient_sample is False
    assert "Erken değerlendirme" in r.note

def test_esik_modlari_ayri_karsilastirilir():
    records=[_perf(1,"E3",LivePerformanceLabel.BASARILI,8), _perf(2,"E3",LivePerformanceLabel.BASARISIZ,-4)]
    r=gercek_sonuclari_degerlendir(records, [], [], threshold_modes={"1":"Kalibre","2":"Varsayılan"})
    assert {x.mode for x in r.threshold_rows} == {"Kalibre","Varsayılan"}
