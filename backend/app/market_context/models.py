\
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class MarketContextDocument:
    """Kullanıcı tarafından yüklenen tek bir piyasa bağlamı belgesini temsil eder.

    Bu model yalnızca bağlamsal karar desteği içindir.
    Teknik skor, aday sıralaması veya AL/SAT kararı üretmez.
    """

    document_id: str
    source: str
    document_date: str
    imported_at: str
    input_type: str
    raw_text: str
    content_hash: str

    index_outlook: str | None = None
    supports: list[str] = field(default_factory=list)
    resistances: list[str] = field(default_factory=list)
    external_market_outlook: str | None = None
    futures_outlook: str | None = None
    macro_risks: list[str] = field(default_factory=list)
    sector_impacts: list[dict[str, Any]] = field(default_factory=list)
    stock_news: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    archive_date: str | None = None
    archive_status: str = "pending"
    ai_eligible: bool = True
    ai_review_status: str = "not_reviewed"

    def validate(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id boş olamaz.")
        if not self.source.strip():
            raise ValueError("source boş olamaz.")
        if not self.document_date.strip():
            raise ValueError("document_date boş olamaz.")
        if self.input_type not in {"text", "txt", "pdf"}:
            raise ValueError("input_type yalnızca text, txt veya pdf olabilir.")
        if not self.raw_text.strip():
            raise ValueError("raw_text boş olamaz.")
        if not self.content_hash.strip():
            raise ValueError("content_hash boş olamaz.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MarketContextDocument":
        document = cls(**payload)
        document.validate()
        return document

    @staticmethod
    def utc_now_iso() -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
