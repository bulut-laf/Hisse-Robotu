from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import re
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from .models import SourceTier
from .source_registry import resolve_source


_MAX_DETAIL_CHARS = 500
_MAX_REFERENCE_CHARS = 800
_DEFAULT_READ_LIMIT = 200
_MAX_READ_LIMIT = 5000


class OfficialSourceOperationError(RuntimeError):
    """Resmî kaynak operasyon günlüğü okunamadığında/yazılamadığında oluşur."""


class OfficialSourceOperationKind(str, Enum):
    PREVIEW_BLOCKED = "PREVIEW_BLOCKED"
    PREVIEW_SUCCESS = "PREVIEW_SUCCESS"
    PREVIEW_ERROR = "PREVIEW_ERROR"
    ARCHIVE_SUCCESS = "ARCHIVE_SUCCESS"
    ARCHIVE_DUPLICATE = "ARCHIVE_DUPLICATE"
    ARCHIVE_ERROR = "ARCHIVE_ERROR"


@dataclass(frozen=True, slots=True)
class OfficialSourceOperationRecord:
    operation_id: str
    source_name: str
    kind: OfficialSourceOperationKind
    occurred_at: datetime
    source_reference: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class OfficialSourceOperationReadResult:
    records: tuple[OfficialSourceOperationRecord, ...]
    invalid_lines: int = 0


@dataclass(frozen=True, slots=True)
class OfficialSourceOperationSummary:
    source_name: str
    last_preview_at: datetime | None = None
    last_preview_kind: OfficialSourceOperationKind | None = None
    last_archive_at: datetime | None = None
    last_archive_kind: OfficialSourceOperationKind | None = None
    last_success_at: datetime | None = None


def default_official_source_operations_path() -> Path:
    return (
        Path.home()
        / ".hisse_robotu"
        / "news_center"
        / "official_source_operations.jsonl"
    )


def _normalized_text(value: object, *, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:max_chars]


def sanitize_source_reference(value: object) -> str:
    """
    Audit günlüğüne kullanıcı bilgisi/query/fragment taşımadan URL referansı üretir.

    Geçersiz veya URL olmayan girdilerde ham metin yerine güvenli bir yer tutucu
    döndürür; parola veya query değeri kalıcılaştırılmaz.
    """
    raw = str(value or "").strip()
    if not raw:
        return ""

    try:
        parsed = urlsplit(raw)
    except ValueError:
        return "[geçersiz-url]"

    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()

    if scheme not in {"http", "https"} or not host:
        return "[geçersiz-url]"

    try:
        port = parsed.port
    except ValueError:
        return "[geçersiz-url]"

    netloc = host
    if port is not None and port not in (80, 443):
        netloc = f"{host}:{port}"

    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    safe = urlunsplit((scheme, netloc, path, "", ""))
    return _normalized_text(safe, max_chars=_MAX_REFERENCE_CHARS)


def _validate_source_name(source_name: str) -> str:
    name = _normalized_text(source_name, max_chars=120)
    resolution = resolve_source(name)
    if (
        resolution is None
        or resolution.canonical_name != name
        or resolution.tier is not SourceTier.TIER_1_OFFICIAL
    ):
        raise OfficialSourceOperationError(
            "Operasyon günlüğü yalnız kayıtlı Tier-1 resmî kaynakları kabul eder."
        )
    return name


def _normalize_datetime(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _record_to_payload(record: OfficialSourceOperationRecord) -> dict[str, object]:
    return {
        "operation_id": record.operation_id,
        "source_name": record.source_name,
        "kind": record.kind.value,
        "occurred_at": record.occurred_at.astimezone(timezone.utc).isoformat(),
        "source_reference": record.source_reference,
        "detail": record.detail,
    }


def _payload_to_record(payload: object) -> OfficialSourceOperationRecord:
    if not isinstance(payload, dict):
        raise ValueError("operation payload object olmalıdır")

    operation_id = _normalized_text(payload.get("operation_id"), max_chars=80)
    source_name = _validate_source_name(str(payload.get("source_name") or ""))
    kind = OfficialSourceOperationKind(str(payload.get("kind") or ""))
    occurred_at = datetime.fromisoformat(str(payload.get("occurred_at") or ""))
    occurred_at = _normalize_datetime(occurred_at)

    if not operation_id:
        raise ValueError("operation_id boş olamaz")

    return OfficialSourceOperationRecord(
        operation_id=operation_id,
        source_name=source_name,
        kind=kind,
        occurred_at=occurred_at,
        source_reference=sanitize_source_reference(
            payload.get("source_reference")
        ),
        detail=_normalized_text(
            payload.get("detail"),
            max_chars=_MAX_DETAIL_CHARS,
        ),
    )


class OfficialSourceOperationStore:
    """
    Kullanıcının açık kaynak-besleme işlemlerini ayrı JSONL audit günlüğünde tutar.

    Haber gövdesi veya adapter yanıtı saklanmaz. Bu günlük ağ isteği başlatmaz.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path)
            if path is not None
            else default_official_source_operations_path()
        )

    def append(
        self,
        source_name: str,
        kind: OfficialSourceOperationKind,
        *,
        source_reference: object = "",
        detail: object = "",
        occurred_at: datetime | None = None,
    ) -> OfficialSourceOperationRecord:
        canonical_name = _validate_source_name(source_name)
        if not isinstance(kind, OfficialSourceOperationKind):
            kind = OfficialSourceOperationKind(str(kind))

        record = OfficialSourceOperationRecord(
            operation_id=uuid4().hex,
            source_name=canonical_name,
            kind=kind,
            occurred_at=_normalize_datetime(occurred_at),
            source_reference=sanitize_source_reference(source_reference),
            detail=_normalized_text(detail, max_chars=_MAX_DETAIL_CHARS),
        )

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    json.dumps(
                        _record_to_payload(record),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                )
                handle.write("\n")
                handle.flush()
        except OSError as exc:
            raise OfficialSourceOperationError(
                f"Operasyon günlüğü yazılamadı: {exc}"
            ) from exc

        return record

    def read(
        self,
        *,
        limit: int = _DEFAULT_READ_LIMIT,
        source_name: str | None = None,
        kinds: Iterable[OfficialSourceOperationKind] | None = None,
    ) -> OfficialSourceOperationReadResult:
        if not isinstance(limit, int) or not 1 <= limit <= _MAX_READ_LIMIT:
            raise ValueError(
                f"limit 1-{_MAX_READ_LIMIT} aralığında tam sayı olmalıdır."
            )

        canonical_filter = (
            _validate_source_name(source_name)
            if source_name is not None
            else None
        )
        kind_filter = (
            frozenset(
                item
                if isinstance(item, OfficialSourceOperationKind)
                else OfficialSourceOperationKind(str(item))
                for item in kinds
            )
            if kinds is not None
            else None
        )

        if not self.path.exists():
            return OfficialSourceOperationReadResult(records=(), invalid_lines=0)

        try:
            with self.path.open("r", encoding="utf-8") as handle:
                lines = deque(handle, maxlen=_MAX_READ_LIMIT * 2)
        except OSError as exc:
            raise OfficialSourceOperationError(
                f"Operasyon günlüğü okunamadı: {exc}"
            ) from exc

        records: list[OfficialSourceOperationRecord] = []
        invalid_lines = 0

        for raw_line in reversed(lines):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = _payload_to_record(json.loads(line))
            except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                invalid_lines += 1
                continue

            if canonical_filter and record.source_name != canonical_filter:
                continue
            if kind_filter is not None and record.kind not in kind_filter:
                continue

            records.append(record)
            if len(records) >= limit:
                break

        return OfficialSourceOperationReadResult(
            records=tuple(records),
            invalid_lines=invalid_lines,
        )


_PREVIEW_KINDS = frozenset(
    {
        OfficialSourceOperationKind.PREVIEW_BLOCKED,
        OfficialSourceOperationKind.PREVIEW_SUCCESS,
        OfficialSourceOperationKind.PREVIEW_ERROR,
    }
)
_ARCHIVE_KINDS = frozenset(
    {
        OfficialSourceOperationKind.ARCHIVE_SUCCESS,
        OfficialSourceOperationKind.ARCHIVE_DUPLICATE,
        OfficialSourceOperationKind.ARCHIVE_ERROR,
    }
)
_SUCCESS_KINDS = frozenset(
    {
        OfficialSourceOperationKind.PREVIEW_SUCCESS,
        OfficialSourceOperationKind.ARCHIVE_SUCCESS,
    }
)


def summarize_official_source_operations(
    records: Iterable[OfficialSourceOperationRecord],
    source_names: Iterable[str],
) -> tuple[OfficialSourceOperationSummary, ...]:
    newest = sorted(
        tuple(records),
        key=lambda item: item.occurred_at,
        reverse=True,
    )

    summaries: list[OfficialSourceOperationSummary] = []
    for source_name in source_names:
        canonical_name = _validate_source_name(source_name)
        source_records = [
            record
            for record in newest
            if record.source_name == canonical_name
        ]

        preview = next(
            (record for record in source_records if record.kind in _PREVIEW_KINDS),
            None,
        )
        archive = next(
            (record for record in source_records if record.kind in _ARCHIVE_KINDS),
            None,
        )
        success = next(
            (record for record in source_records if record.kind in _SUCCESS_KINDS),
            None,
        )

        summaries.append(
            OfficialSourceOperationSummary(
                source_name=canonical_name,
                last_preview_at=preview.occurred_at if preview else None,
                last_preview_kind=preview.kind if preview else None,
                last_archive_at=archive.occurred_at if archive else None,
                last_archive_kind=archive.kind if archive else None,
                last_success_at=success.occurred_at if success else None,
            )
        )

    return tuple(summaries)
