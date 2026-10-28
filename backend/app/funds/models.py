"""Typed data model for fund research; no investment recommendations."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urlparse
import re

class FundType(str, Enum):
    MUTUAL_FUND = "mutual_fund"
    UCITS_ETF = "ucits_etf"
    ETC = "etc"
    MONEY_MARKET = "money_market"
    BOND_FUND = "bond_fund"
    MULTI_ASSET = "multi_asset"
    OTHER = "other"

class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    UNAVAILABLE = "unavailable"

@dataclass(frozen=True)
class FundSource:
    url: str
    source_type: str
    checked_at: str | None = None
    notes: str = ""
    def __post_init__(self):
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Source URL must be absolute HTTP(S): {self.url!r}")
        if not self.source_type.strip():
            raise ValueError("source_type must not be blank")

@dataclass(frozen=True)
class FundRecord:
    isin: str
    name: str
    fund_type: FundType
    domicile: str | None = None
    base_currency: str | None = None
    share_class_currency: str | None = None
    provider: str | None = None
    accumulating: bool | None = None
    ongoing_charge_pct: float | None = None
    management_fee_pct: float | None = None
    risk_indicator: int | None = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    sources: tuple[FundSource, ...] = field(default_factory=tuple)
    tags: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""
    def __post_init__(self):
        normalized = self.isin.replace(" ", "").upper()
        object.__setattr__(self, "isin", normalized)
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", normalized):
            raise ValueError(f"Invalid ISIN shape: {self.isin!r}")
        if not self.name.strip(): raise ValueError("Fund name must not be blank")
        for key in ("ongoing_charge_pct", "management_fee_pct"):
            value = getattr(self, key)
            if value is not None and not 0 <= value <= 100: raise ValueError(f"{key} must be between 0 and 100")
        if self.risk_indicator is not None and self.risk_indicator not in range(1, 8):
            raise ValueError("risk_indicator must be an integer from 1 to 7")
        if len({s.url for s in self.sources}) != len(self.sources): raise ValueError("Duplicate source URLs")
    def to_dict(self) -> dict[str, Any]:
        return {"isin":self.isin,"name":self.name,"fund_type":self.fund_type.value,"domicile":self.domicile,
          "base_currency":self.base_currency,"share_class_currency":self.share_class_currency,"provider":self.provider,
          "accumulating":self.accumulating,"ongoing_charge_pct":self.ongoing_charge_pct,"management_fee_pct":self.management_fee_pct,
          "risk_indicator":self.risk_indicator,"verification_status":self.verification_status.value,
          "sources":[{"url":s.url,"source_type":s.source_type,"checked_at":s.checked_at,"notes":s.notes} for s in self.sources],
          "tags":list(self.tags),"notes":self.notes}
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FundRecord":
        d=dict(data); d["fund_type"]=FundType(d["fund_type"])
        d["verification_status"]=VerificationStatus(d.get("verification_status","unverified"))
        d["sources"]=tuple(FundSource(**s) for s in d.get("sources",[])); d["tags"]=tuple(d.get("tags",[]))
        return cls(**d)
