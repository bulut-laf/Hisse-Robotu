from dataclasses import dataclass
from datetime import date
import json
from backend.app.prebreakout.prebreakout_validation_evidence import build_prebreakout_validation_evidence_rows, persist_prebreakout_validation_evidence
@dataclass(frozen=True)
class Replay: momentum_score: float; trend_score: float; volume_ratio: float; resistance_distance_pct: float; risk_reward: float
@dataclass(frozen=True)
class Record: symbol: str; cutoff_date: date; performance_label: str; replay: Replay
@dataclass(frozen=True)
class Result: records: tuple[Record,...]
def test_build_rows_reads_existing_result_records():
    r=Result(records=(Record("TEST",date(2026,8,17),"SUCCESS",Replay(70,12,1.8,1.2,2.0)),))
    rows=build_prebreakout_validation_evidence_rows(r)
    assert len(rows)==1 and rows[0]["symbol"]=="TEST" and rows[0]["performance_label"]=="SUCCESS" and rows[0]["replay.risk_reward"]==2.0
def test_persist_writes_json_and_csv_sidecars(tmp_path):
    r=Result(records=(Record("TEST",date(2026,8,17),"FALSE_POSITIVE",Replay(60,9,1.1,2.5,1.3)),))
    written=persist_prebreakout_validation_evidence(r,output_dir=tmp_path)
    assert written is not None
    jp,cp=written; assert jp.exists() and cp.exists(); data=json.loads(jp.read_text(encoding="utf-8")); assert data[0]["symbol"]=="TEST"
