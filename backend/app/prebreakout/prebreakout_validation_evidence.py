from __future__ import annotations
import csv, json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

def _plain(v: Any) -> Any:
    if is_dataclass(v): return {k:_plain(x) for k,x in asdict(v).items()}
    if isinstance(v,Enum): return _plain(v.value)
    if isinstance(v,(datetime,date)): return v.isoformat()
    if isinstance(v,dict): return {str(k):_plain(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,set)): return [_plain(x) for x in v]
    if isinstance(v,Path): return str(v)
    if hasattr(v,"__dict__"): return {str(k):_plain(x) for k,x in vars(v).items() if not str(k).startswith("_")}
    return v

def _flatten(prefix: str, v: Any, out: dict[str,Any]) -> None:
    if isinstance(v,dict):
        for k,x in v.items(): _flatten(f"{prefix}.{k}" if prefix else str(k),x,out)
    elif isinstance(v,list): out[prefix]=json.dumps(v,ensure_ascii=False,sort_keys=True,default=str)
    else: out[prefix]=v

def _records(v: Any) -> list[Any]:
    if v is None: return []
    if isinstance(v,(list,tuple)): return list(v)
    if isinstance(v,dict):
        for k in ("records","validation_records","results","items","rows"):
            x=v.get(k)
            if isinstance(x,(list,tuple)): return list(x)
    for k in ("records","validation_records","results","items","rows"):
        x=getattr(v,k,None)
        if isinstance(x,(list,tuple)): return list(x)
    return []

def build_prebreakout_validation_evidence_rows(v: Any) -> list[dict[str,Any]]:
    rows=[]
    for r in _records(v):
        p=_plain(r); p=p if isinstance(p,dict) else {"record":p}; flat={}; _flatten("",p,flat); rows.append(flat)
    return rows

def persist_prebreakout_validation_evidence(v: Any, *, output_dir: Path|None=None):
    rows=build_prebreakout_validation_evidence_rows(v)
    if not rows: return None
    base=output_dir or (Path.home()/".hisse_robotu"/"prebreakout_validation_evidence"); base.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    jp=base/f"prebreakout_validation_rows_{stamp}.json"; cp=base/f"prebreakout_validation_rows_{stamp}.csv"
    jp.write_text(json.dumps(rows,ensure_ascii=False,indent=2,sort_keys=True,default=str),encoding="utf-8")
    fields=sorted({k for r in rows for k in r})
    with cp.open("w",encoding="utf-8-sig",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    return jp,cp
