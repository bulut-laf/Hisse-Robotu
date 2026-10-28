"""ISIN-keyed canonical fund universe with explicit evidence handling."""
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import json
from .models import FundRecord

class UniverseValidationError(ValueError): pass

@dataclass
class FundUniverse:
    records: dict[str, FundRecord]
    @classmethod
    def empty(cls): return cls(records={})
    @classmethod
    def from_records(cls, records: Iterable[FundRecord]):
        obj=cls.empty()
        for record in records: obj.upsert(record)
        return obj
    def upsert(self, record: FundRecord):
        current=self.records.get(record.isin)
        if current is None: self.records[record.isin]=record; return
        if current.name.casefold()!=record.name.casefold():
            raise UniverseValidationError(f"ISIN collision for {record.isin}: {current.name!r} vs {record.name!r}; reconcile explicitly")
        merged={s.url:s for s in (*current.sources,*record.sources)}
        data=current.to_dict(); incoming=record.to_dict()
        for key,value in incoming.items():
            if key in {"sources","verification_status"}: continue
            if value not in (None,"",[],{}): data[key]=value
        data["sources"]=[{"url":s.url,"source_type":s.source_type,"checked_at":s.checked_at,"notes":s.notes} for s in merged.values()]
        self.records[record.isin]=FundRecord.from_dict(data)
    def get(self, isin): return self.records.get(isin.replace(" ","").upper())
    def list_records(self): return sorted(self.records.values(),key=lambda x:(x.name.casefold(),x.isin))
    def save(self,path):
        target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
        payload={"schema_version":1,"identity_key":"isin","records":[r.to_dict() for r in self.list_records()]}
        target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    @classmethod
    def load(cls,path):
        source=Path(path)
        try: payload=json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError: return cls.empty()
        except (json.JSONDecodeError,UnicodeDecodeError) as exc: raise UniverseValidationError(f"Cannot parse {source}: {exc}") from exc
        if payload.get("schema_version")!=1: raise UniverseValidationError(f"Unsupported schema_version: {payload.get('schema_version')!r}")
        if not isinstance(payload.get("records"),list): raise UniverseValidationError("records must be a JSON array")
        return cls.from_records(FundRecord.from_dict(row) for row in payload["records"])
