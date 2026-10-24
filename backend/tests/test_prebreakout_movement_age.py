from datetime import date
import pytest
from backend.app.prebreakout.prebreakout_movement_age import *

def snap(day,rank,score,price,momentum):
    return RankingSnapshot(date(2026,7,day),rank,score,price,momentum)

def test_bos_gecmis_yetersiz():
    assert analyze_movement_age(()).phase is MovementPhase.YETERSIZ

def test_11_30_bandinda_yukselen_sira_erken_radar():
    h=(snap(1,34,54,100,45),snap(2,28,58,102,48),snap(3,23,63,104,52),snap(4,18,68,107,56))
    r=analyze_movement_age(h)
    assert r.early_radar is EarlyRadarState.YUKSEK_ONCELIK
    assert r.phase is MovementPhase.GELISIYOR
    assert r.rank_velocity>0 and r.score_velocity>0

def test_11_30_bandinda_ama_ivmesiz_izle():
    h=(snap(1,20,60,100,50),snap(2,21,60,100,50),snap(3,22,60,100,50))
    assert analyze_movement_age(h).early_radar is EarlyRadarState.IZLE

def test_ilk5_ve_uzun_hareket_kar_koruma():
    h=(snap(1,25,55,100,48),snap(2,20,60,104,52),snap(3,15,66,108,56),snap(4,10,72,112,60),
       snap(5,7,78,116,64),snap(6,4,84,120,67),snap(7,3,90,125,69))
    r=analyze_movement_age(h)
    assert r.maturity_warning is MaturityWarning.KAR_KORUMA
    assert r.phase is MovementPhase.OLGUN
    assert r.realized_move_pct==pytest.approx(25)

def test_ilk5_sonra_skor_dusuyorsa_yoruluyor():
    h=(snap(1,25,60,100,50),snap(2,18,70,106,56),snap(3,10,82,112,62),
       snap(4,5,91,120,68),snap(5,4,88,119,65),snap(6,5,84,117,61))
    r=analyze_movement_age(h,maturity_min_sessions=5)
    assert r.maturity_warning is MaturityWarning.KAR_KORUMA
    assert r.phase is MovementPhase.YORULUYOR

def test_ilk5_hizli_geldiyse_sadece_olgunlasiyor():
    r=analyze_movement_age((snap(1,12,72,100,58),snap(2,4,83,106,64)))
    assert r.maturity_warning is MaturityWarning.OLGUNLASIYOR

def test_ilk_gorunme_ve_bant_tarihleri():
    h=(snap(1,35,50,100,45),snap(2,29,58,102,50),snap(3,9,70,107,58),snap(4,5,82,112,64))
    r=analyze_movement_age(h)
    assert r.first_seen_date==date(2026,7,1)
    assert r.first_top30_date==date(2026,7,2)
    assert r.first_top10_date==date(2026,7,3)
    assert r.first_top5_date==date(2026,7,4)

def test_top5_sonrasi_1_3_5_gun_performans():
    p=top5_forward_performance(entry_price=100,future_closes=(99,98,97,96,95))
    assert p["1d"]==pytest.approx(-1) and p["3d"]==pytest.approx(-3) and p["5d"]==pytest.approx(-5)

def test_top5_eksik_ileri_gun_none():
    p=top5_forward_performance(entry_price=100,future_closes=(101,))
    assert p["1d"]==pytest.approx(1) and p["3d"] is None and p["5d"] is None

def test_gecersiz_rank_hata():
    with pytest.raises(ValueError): snap(1,0,50,100,45)

def test_gecersiz_score_hata():
    with pytest.raises(ValueError): RankingSnapshot(date(2026,7,1),10,101,100,50)

def test_gecersiz_fiyat_hata():
    with pytest.raises(ValueError): RankingSnapshot(date(2026,7,1),10,50,0,50)

def test_peak_drop_esigi_kucuk_oynamayi_yorulma_saymaz():
    h=(snap(1,20,60,100,50),snap(2,10,75,108,58),snap(3,4,90,120,65),snap(4,4,88.5,121,64))
    r=analyze_movement_age(h,maturity_min_sessions=3,peak_score_drop=3)
    assert r.phase is MovementPhase.OLGUN
