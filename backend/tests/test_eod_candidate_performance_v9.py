from datetime import datetime
import pytest
from app.analysis.eod_candidate_performance import CONTRACT_ID, EodCandidatePerformanceJsonStore, calculate_eod_candidate_performance

def _history():
    return {"ABC": {"2026-10-12": {"high":103,"low":99,"close":102}, "2026-10-13": {"high":106,"low":98,"close":104}, "2026-10-14": {"high":105,"low":97,"close":101}, "2026-10-15": {"high":108,"low":100,"close":107}, "2026-10-16": {"high":110,"low":102,"close":109}}}

def test_calculates_t1_t3_t5_returns_and_mfe_mae():
    result=calculate_eod_candidate_performance(run_date="2026-10-09",candidate_symbols=("ABC",),reference_prices={"ABC":100},price_history=_history())
    assert result["contract_id"]==CONTRACT_ID and result["status"]=="SUCCESS"
    h=result["candidates"][0]["horizons"]
    assert [x["horizon"] for x in h]==[1,3,5]
    assert h[0]["return"]==pytest.approx(.02) and h[0]["mfe"]==pytest.approx(.03) and h[0]["mae"]==pytest.approx(-.01)
    assert h[2]["return"]==pytest.approx(.09) and h[2]["mfe"]==pytest.approx(.10) and h[2]["mae"]==pytest.approx(-.03)

def test_missing_reference_price_is_pending_not_zero_return():
    r=calculate_eod_candidate_performance(run_date="2026-10-09",candidate_symbols=("ABC",),reference_prices={},price_history=_history())
    assert r["status"]=="PENDING_DATA" and r["candidates"][0]["reason"]=="REFERENCE_PRICE_MISSING" and r["candidates"][0]["horizons"]==[]

def test_fewer_than_five_sessions_stays_pending():
    hist=dict(list(_history()["ABC"].items())[:3])
    r=calculate_eod_candidate_performance(run_date="2026-10-09",candidate_symbols=("ABC",),reference_prices={"ABC":100},price_history={"ABC":hist})
    assert r["status"]=="PENDING_DATA" and [x["horizon"] for x in r["candidates"][0]["horizons"]]==[1,3]

def test_invalid_ohlc_rows_are_not_used():
    hist=_history(); hist["ABC"]["2026-10-12"]={"high":98,"low":100,"close":99}
    r=calculate_eod_candidate_performance(run_date="2026-10-09",candidate_symbols=("ABC",),reference_prices={"ABC":100},price_history=hist)
    assert r["status"]=="PENDING_DATA" and r["candidates"][0]["horizons"][0]["target_date"]=="2026-10-13"

def test_archive_replaces_same_run_and_phase(tmp_path):
    store=EodCandidatePerformanceJsonStore(tmp_path/"outcomes.json")
    first={"contract_id":CONTRACT_ID,"run_date":"2026-10-09","phase":"CANONICAL_CLOSE","status":"PENDING_DATA"}
    store.save_record(first,recorded_at=datetime(2026,10,9)); store.save_record({**first,"status":"SUCCESS"},recorded_at=datetime(2026,10,10))
    records=store.load()["records"]
    assert len(records)==1 and records[0]["status"]=="SUCCESS" and records[0]["recorded_at"]=="2026-10-10T00:00:00"
