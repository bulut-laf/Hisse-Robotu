\
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DailyArchiveDocumentRef:
    document_id: str
    source: str
    document_date: str
    input_type: str
    content_hash: str
    processed_path: str | None = None
    raw_path: str | None = None


@dataclass(slots=True)
class DailyArchiveManifest:
    """Bir işlem gününe yüklenen tüm raporların indeksidir.

    İleride çoklu-rapor AI değerlendirmesi bu manifest üzerinden çalışabilir.
    AI değerlendirmesi bu sprintte üretilmez.
    """

    date: str
    documents: list[DailyArchiveDocumentRef] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    ai_review_status: str = "not_reviewed"
    ai_review_id: str | None = None

    @property
    def document_count(self) -> int:
        return len(self.documents)

    def has_document_id(self, document_id: str) -> bool:
        return any(item.document_id == document_id for item in self.documents)

    def has_content_hash(self, content_hash: str) -> bool:
        return any(item.content_hash == content_hash for item in self.documents)

    def add_document(self, item: DailyArchiveDocumentRef) -> bool:
        """Yeni belge ekler.

        Aynı document_id veya aynı content_hash varsa False döner.
        Böylece arşiv seviyesinde basit tekrar kontrolü sağlanır.
        """
        if self.has_document_id(item.document_id):
            return False
        if self.has_content_hash(item.content_hash):
            return False

        self.documents.append(item)

        if item.source and item.source not in self.sources:
            self.sources.append(item.source)
            self.sources.sort()

        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "document_count": self.document_count,
            "documents": [asdict(item) for item in self.documents],
            "sources": list(self.sources),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "ai_review_status": self.ai_review_status,
            "ai_review_id": self.ai_review_id,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DailyArchiveManifest":
        documents = [
            DailyArchiveDocumentRef(**item)
            for item in payload.get("documents", [])
        ]
        return cls(
            date=payload["date"],
            documents=documents,
            sources=list(payload.get("sources", [])),
            created_at=payload.get("created_at"),
            updated_at=payload.get("updated_at"),
            ai_review_status=payload.get("ai_review_status", "not_reviewed"),
            ai_review_id=payload.get("ai_review_id"),
        )

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    @classmethod
    def load(cls, path: str | Path) -> "DailyArchiveManifest":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)
