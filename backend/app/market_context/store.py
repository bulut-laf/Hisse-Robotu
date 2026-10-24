from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from .archive import DailyArchiveDocumentRef, DailyArchiveManifest
from .models import MarketContextDocument
from .source_normalization import normalize_source_name


class DuplicateMarketContextError(ValueError):
    """Aynı içerik daha önce arşivlenmişse yükseltilir."""


class MarketContextStore:
    """Piyasa bağlamı belgelerinin ham/işlenmiş/arşiv katmanını yönetir."""

    def __init__(self, data_root: str | Path):
        self.data_root = Path(data_root)
        self.raw_root = self.data_root / "market_context_raw"
        self.processed_root = self.data_root / "market_context_processed"
        self.archive_root = self.data_root / "market_context_archive"

    def ensure_directories(self) -> None:
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.processed_root.mkdir(parents=True, exist_ok=True)
        self.archive_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_text(text: str) -> str:
        value = text.replace("\r\n", "\n").replace("\r", "\n")
        value = "\n".join(line.strip() for line in value.split("\n"))
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()

    @classmethod
    def content_hash(cls, text: str) -> str:
        normalized = cls.normalize_text(text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _date_dir(self, root: Path, document_date: str) -> Path:
        return root / document_date

    def _manifest_path(self, document_date: str) -> Path:
        return self._date_dir(self.archive_root, document_date) / "daily_manifest.json"

    def load_manifest(self, document_date: str) -> DailyArchiveManifest:
        path = self._manifest_path(document_date)
        if path.exists():
            return DailyArchiveManifest.load(path)

        now = self._utc_now_iso()
        return DailyArchiveManifest(
            date=document_date,
            created_at=now,
            updated_at=now,
        )

    def is_duplicate(self, document_date: str, content_hash: str) -> bool:
        return self.load_manifest(document_date).has_content_hash(content_hash)

    def save_text_document(
        self,
        document: MarketContextDocument,
        *,
        raw_extension: str = ".txt",
    ) -> MarketContextDocument:
        self.ensure_directories()
        document.validate()

        computed_hash = self.content_hash(document.raw_text)
        document = replace(
            document,
            content_hash=computed_hash,
            source=normalize_source_name(document.source),
        )

        manifest = self.load_manifest(document.document_date)
        if manifest.has_content_hash(computed_hash):
            raise DuplicateMarketContextError("Bu içerik daha önce yüklenmiş.")

        raw_dir = self._date_dir(self.raw_root, document.document_date)
        processed_dir = self._date_dir(self.processed_root, document.document_date)
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)

        extension = raw_extension if raw_extension.startswith(".") else f".{raw_extension}"
        raw_path = raw_dir / f"{document.document_id}{extension}"
        processed_path = processed_dir / f"{document.document_id}.json"

        raw_path.write_text(document.raw_text, encoding="utf-8")

        archived_document = replace(
            document,
            archive_date=document.document_date,
            archive_status="archived",
        )

        processed_path.write_text(
            json.dumps(
                archived_document.to_dict(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        added = manifest.add_document(
            DailyArchiveDocumentRef(
                document_id=archived_document.document_id,
                source=archived_document.source,
                document_date=archived_document.document_date,
                input_type=archived_document.input_type,
                content_hash=archived_document.content_hash,
                raw_path=str(raw_path.relative_to(self.data_root)),
                processed_path=str(processed_path.relative_to(self.data_root)),
            )
        )

        if not added:
            raw_path.unlink(missing_ok=True)
            processed_path.unlink(missing_ok=True)
            raise DuplicateMarketContextError("Bu içerik daha önce yüklenmiş.")

        manifest.updated_at = self._utc_now_iso()
        manifest.save(self._manifest_path(document.document_date))

        return archived_document

    def save_binary_raw_file(
        self,
        *,
        source_path: str | Path,
        document_id: str,
        document_date: str,
        extension: str,
    ) -> Path:
        self.ensure_directories()
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(source)

        raw_dir = self._date_dir(self.raw_root, document_date)
        raw_dir.mkdir(parents=True, exist_ok=True)

        suffix = extension if extension.startswith(".") else f".{extension}"
        target = raw_dir / f"{document_id}{suffix}"
        shutil.copy2(source, target)
        return target

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
