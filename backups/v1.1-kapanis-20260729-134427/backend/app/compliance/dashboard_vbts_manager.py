from __future__ import annotations

import csv
import os
import re
import tempfile
import json
import shutil
import hashlib
import io
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

CSV_COLUMNS = (
    "symbol",
    "measure_type",
    "start_date",
    "end_date",
    "source_reference",
)

STATUS_ACTIVE = "Aktif"
STATUS_FUTURE = "Gelecekte başlayacak"
STATUS_EXPIRED = "Süresi dolmuş"

_GENERIC_REFERENCES = {
    "kap bildirim numarası",
    "kap bildirim numarasi",
    "bildirim numarası",
    "bildirim numarasi",
    "örnek",
    "ornek",
    "test",
}


class DashboardVbtsManagerError(ValueError):
    pass


@dataclass(frozen=True)
class DashboardVbtsRecord:
    symbol: str
    measure_type: str
    start_date: date
    end_date: date
    source_reference: str

    @property
    def record_key(self) -> str:
        return "|".join(
            (
                self.symbol,
                self.measure_type,
                self.start_date.isoformat(),
                self.end_date.isoformat(),
                self.source_reference,
            )
        )

    def status(self, on_date: date | None = None) -> str:
        current = on_date or date.today()
        if current < self.start_date:
            return STATUS_FUTURE
        if current > self.end_date:
            return STATUS_EXPIRED
        return STATUS_ACTIVE

    def as_csv_row(self) -> dict[str, str]:
        return {
            "symbol": self.symbol.removesuffix(".IS"),
            "measure_type": self.measure_type,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "source_reference": self.source_reference,
        }

    def as_display_row(self, on_date: date | None = None) -> dict[str, str]:
        return {
            "Hisse": self.symbol.removesuffix(".IS"),
            "Tedbir": self.measure_type,
            "Başlangıç": self.start_date.isoformat(),
            "Bitiş": self.end_date.isoformat(),
            "Durum": self.status(on_date),
            "KAP referansı": self.source_reference,
        }


@dataclass(frozen=True)
class DashboardVbtsLifecycle:
    active: tuple[DashboardVbtsRecord, ...]
    future: tuple[DashboardVbtsRecord, ...]
    expired: tuple[DashboardVbtsRecord, ...]

    @property
    def all_records(self) -> tuple[DashboardVbtsRecord, ...]:
        return self.active + self.future + self.expired


def default_vbts_csv_path(project_root: Path | None = None) -> Path:
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]
    return project_root / "data" / "vbts" / "vbts_guncel.csv"


def default_vbts_registry_path(project_root: Path | None = None) -> Path:
    if project_root is None:
        project_root = Path(__file__).resolve().parents[3]
    return project_root / "data" / "vbts" / "vbts_kayitlari.csv"


def configured_vbts_csv_path(project_root: Path | None = None) -> Path:
    configured = os.getenv("HISSE_ROBOTU_VBTS_CSV_PATH", "").strip()
    return Path(configured) if configured else default_vbts_csv_path(project_root)


def registry_path_for(csv_path: Path) -> Path:
    return csv_path.with_name("vbts_kayitlari.csv")


def _normalize_symbol(value: str) -> str:
    normalized = value.strip().upper()
    if normalized.endswith(".IS"):
        normalized = normalized[:-3]

    if not re.fullmatch(r"[A-Z0-9]{3,10}", normalized):
        raise DashboardVbtsManagerError("Hisse sembolü geçersizdir.")

    return normalized + ".IS"


def _clean_required(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise DashboardVbtsManagerError(f"{field_name} boş bırakılamaz.")
    return cleaned


def _parse_date(value: str | date, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise DashboardVbtsManagerError(
            f"{field_name} YYYY-MM-DD biçiminde olmalıdır."
        ) from exc


def build_vbts_record(
    *,
    symbol: str,
    measure_type: str,
    start_date: str | date,
    end_date: str | date,
    source_reference: str,
) -> DashboardVbtsRecord:
    normalized_symbol = _normalize_symbol(symbol)
    cleaned_measure = _clean_required(measure_type, "VBTS tedbir türü")
    cleaned_reference = _clean_required(
        source_reference,
        "Resmî KAP bildirim referansı",
    )

    if cleaned_reference.casefold() in _GENERIC_REFERENCES:
        raise DashboardVbtsManagerError(
            "Örnek metin yerine gerçek resmî KAP bildirim referansı girilmelidir."
        )

    parsed_start = _parse_date(start_date, "Başlangıç tarihi")
    parsed_end = _parse_date(end_date, "Bitiş tarihi")
    if parsed_end < parsed_start:
        raise DashboardVbtsManagerError(
            "Bitiş tarihi başlangıç tarihinden önce olamaz."
        )

    return DashboardVbtsRecord(
        symbol=normalized_symbol,
        measure_type=cleaned_measure,
        start_date=parsed_start,
        end_date=parsed_end,
        source_reference=cleaned_reference,
    )


def _read_records(path: Path) -> tuple[DashboardVbtsRecord, ...]:
    if not path.exists():
        return ()

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
                raise DashboardVbtsManagerError(
                    "VBTS CSV sütunları beklenen şemayla uyumlu değildir."
                )
            return tuple(
                build_vbts_record(
                    symbol=row["symbol"],
                    measure_type=row["measure_type"],
                    start_date=row["start_date"],
                    end_date=row["end_date"],
                    source_reference=row["source_reference"],
                )
                for row in reader
            )
    except OSError as exc:
        raise DashboardVbtsManagerError(
            f"VBTS CSV dosyası okunamadı: {exc}"
        ) from exc


def _write_records_atomic(
    path: Path,
    records: tuple[DashboardVbtsRecord, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        path.unlink(missing_ok=True)
        return

    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8-sig",
            newline="",
            delete=False,
            dir=path.parent,
            prefix=f".{path.stem}-",
            suffix=".tmp",
        ) as stream:
            temp_name = stream.name
            writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(record.as_csv_row() for record in records)

        Path(temp_name).replace(path)
    except OSError as exc:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
        raise DashboardVbtsManagerError(
            f"VBTS CSV dosyası yazılamadı: {exc}"
        ) from exc


def _deduplicate(
    records: tuple[DashboardVbtsRecord, ...],
) -> tuple[DashboardVbtsRecord, ...]:
    seen: set[str] = set()
    unique: list[DashboardVbtsRecord] = []
    for record in records:
        if record.record_key not in seen:
            seen.add(record.record_key)
            unique.append(record)
    return tuple(unique)


def _ensure_registry(csv_path: Path) -> Path:
    registry_path = registry_path_for(csv_path)
    if registry_path.exists():
        return registry_path

    existing = _read_records(csv_path)
    if existing:
        _write_records_atomic(registry_path, _deduplicate(existing))
    return registry_path


def list_vbts_records(csv_path: Path) -> tuple[DashboardVbtsRecord, ...]:
    registry_path = _ensure_registry(csv_path)
    if registry_path.exists():
        return _read_records(registry_path)
    return _read_records(csv_path)


def classify_vbts_records(
    records: tuple[DashboardVbtsRecord, ...],
    on_date: date | None = None,
) -> DashboardVbtsLifecycle:
    current = on_date or date.today()
    active = tuple(record for record in records if record.status(current) == STATUS_ACTIVE)
    future = tuple(record for record in records if record.status(current) == STATUS_FUTURE)
    expired = tuple(record for record in records if record.status(current) == STATUS_EXPIRED)
    return DashboardVbtsLifecycle(
        active=active,
        future=future,
        expired=expired,
    )


def sync_active_vbts_csv(
    csv_path: Path,
    records: tuple[DashboardVbtsRecord, ...] | None = None,
    on_date: date | None = None,
) -> DashboardVbtsLifecycle:
    all_records = records if records is not None else list_vbts_records(csv_path)
    lifecycle = classify_vbts_records(all_records, on_date)
    _write_records_atomic(csv_path, lifecycle.active)
    return lifecycle


def activate_manual_vbts_source(csv_path: Path) -> None:
    os.environ["HISSE_ROBOTU_VBTS_SOURCE"] = "manual_csv"
    os.environ["HISSE_ROBOTU_VBTS_CSV_PATH"] = str(csv_path)
    os.environ.setdefault("HISSE_ROBOTU_VBTS_CSV_MAX_AGE_HOURS", "24")


def add_vbts_record(
    csv_path: Path,
    record: DashboardVbtsRecord,
) -> tuple[DashboardVbtsRecord, ...]:
    records = list_vbts_records(csv_path)
    if any(item.record_key == record.record_key for item in records):
        raise DashboardVbtsManagerError("Aynı VBTS kaydı zaten mevcut.")

    updated = records + (record,)
    registry_path = registry_path_for(csv_path)
    _create_backup(registry_path, "kayit_ekleme")
    _create_backup(csv_path, "kayit_ekleme")
    _write_records_atomic(registry_path, updated)
    sync_active_vbts_csv(csv_path, updated)
    activate_manual_vbts_source(csv_path)
    _append_audit(
        csv_path,
        action="KAYIT_EKLENDI",
        detail=f"{record.symbol} VBTS kaydı eklendi.",
        record_key=record.record_key,
    )
    return updated


def delete_vbts_record(
    csv_path: Path,
    record_key: str,
) -> tuple[DashboardVbtsRecord, ...]:
    records = list_vbts_records(csv_path)
    updated = tuple(item for item in records if item.record_key != record_key)

    if len(updated) == len(records):
        raise DashboardVbtsManagerError("Silinecek VBTS kaydı bulunamadı.")

    registry_path = registry_path_for(csv_path)
    _create_backup(registry_path, "kayit_silme")
    _create_backup(csv_path, "kayit_silme")
    _write_records_atomic(registry_path, updated)
    sync_active_vbts_csv(csv_path, updated)
    if updated:
        activate_manual_vbts_source(csv_path)
    _append_audit(
        csv_path,
        action="KAYIT_SILINDI",
        detail="Seçili VBTS kaydı silindi.",
        record_key=record_key,
    )
    return updated


def purge_expired_vbts_records(
    csv_path: Path,
    on_date: date | None = None,
) -> tuple[DashboardVbtsRecord, ...]:
    records = list_vbts_records(csv_path)
    lifecycle = classify_vbts_records(records, on_date)
    remaining = lifecycle.active + lifecycle.future
    registry_path = registry_path_for(csv_path)
    _create_backup(registry_path, "suresi_dolmus_temizligi")
    _create_backup(csv_path, "suresi_dolmus_temizligi")
    removed_count = len(records) - len(remaining)
    _write_records_atomic(registry_path, remaining)
    sync_active_vbts_csv(csv_path, remaining, on_date)
    if remaining:
        activate_manual_vbts_source(csv_path)
    _append_audit(
        csv_path,
        action="SURESI_DOLMUS_KAYITLAR_TEMIZLENDI",
        detail=f"{removed_count} süresi dolmuş kayıt temizlendi.",
    )
    return remaining


@dataclass(frozen=True)
class DashboardVbtsOperationalStatus:
    synchronized_at: str
    active_count: int
    future_count: int
    expired_count: int
    audit_log_path: Path
    last_action: str | None
    last_action_at: str | None


def audit_log_path_for(csv_path: Path) -> Path:
    return csv_path.with_name("vbts_denetim.jsonl")


def backup_directory_for(csv_path: Path) -> Path:
    return csv_path.parent / "yedekler"


def synchronization_state_path_for(csv_path: Path) -> Path:
    return csv_path.with_name("vbts_senkronizasyon_durumu.json")


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _create_backup(path: Path, action: str) -> Path | None:
    if not path.exists():
        return None

    backup_dir = backup_directory_for(path)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_action = re.sub(r"[^a-zA-Z0-9_-]+", "_", action).strip("_") or "islem"
    backup_path = backup_dir / f"{path.stem}_{timestamp}_{safe_action}{path.suffix}"
    try:
        shutil.copy2(path, backup_path)
    except OSError as exc:
        raise DashboardVbtsManagerError(
            f"VBTS yedeği oluşturulamadı: {exc}"
        ) from exc
    register_backup_integrity(path.with_name("vbts_guncel.csv"), backup_path)
    return backup_path


def _append_audit(
    csv_path: Path,
    *,
    action: str,
    detail: str,
    record_key: str | None = None,
) -> None:
    path = audit_log_path_for(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp_utc": _utc_now_text(),
        "action": action,
        "detail": detail,
        "record_key": record_key,
    }
    try:
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError as exc:
        raise DashboardVbtsManagerError(
            f"VBTS denetim günlüğü yazılamadı: {exc}"
        ) from exc


def read_last_audit_event(csv_path: Path) -> dict[str, object] | None:
    path = audit_log_path_for(csv_path)
    if not path.exists():
        return None
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    except OSError as exc:
        raise DashboardVbtsManagerError(
            f"VBTS denetim günlüğü okunamadı: {exc}"
        ) from exc
    for line in reversed(lines):
        if line:
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DashboardVbtsManagerError(
                    "VBTS denetim günlüğü bozuk."
                ) from exc
            if not isinstance(value, dict):
                raise DashboardVbtsManagerError(
                    "VBTS denetim günlüğü geçersiz."
                )
            return value
    return None


def _write_sync_state(
    csv_path: Path,
    lifecycle: DashboardVbtsLifecycle,
) -> None:
    state_path = synchronization_state_path_for(csv_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "synchronized_at_utc": _utc_now_text(),
        "synchronized_for_date": date.today().isoformat(),
        "active_count": len(lifecycle.active),
        "future_count": len(lifecycle.future),
        "expired_count": len(lifecycle.expired),
    }
    temp_path = state_path.with_suffix(".tmp")
    try:
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(state_path)
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        raise DashboardVbtsManagerError(
            f"VBTS senkronizasyon durumu yazılamadı: {exc}"
        ) from exc


def read_operational_status(
    csv_path: Path,
    lifecycle: DashboardVbtsLifecycle,
) -> DashboardVbtsOperationalStatus:
    state_path = synchronization_state_path_for(csv_path)
    synchronized_at = "—"
    if state_path.exists():
        try:
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            synchronized_at = str(payload.get("synchronized_at_utc") or "—")
        except (OSError, json.JSONDecodeError, AttributeError) as exc:
            raise DashboardVbtsManagerError(
                "VBTS senkronizasyon durum dosyası bozuk."
            ) from exc

    last_event = read_last_audit_event(csv_path)
    return DashboardVbtsOperationalStatus(
        synchronized_at=synchronized_at,
        active_count=len(lifecycle.active),
        future_count=len(lifecycle.future),
        expired_count=len(lifecycle.expired),
        audit_log_path=audit_log_path_for(csv_path),
        last_action=(
            str(last_event.get("action"))
            if last_event and last_event.get("action") is not None
            else None
        ),
        last_action_at=(
            str(last_event.get("timestamp_utc"))
            if last_event and last_event.get("timestamp_utc") is not None
            else None
        ),
    )


def synchronize_vbts_operational_state(
    csv_path: Path,
    on_date: date | None = None,
) -> DashboardVbtsLifecycle:
    records = list_vbts_records(csv_path)
    lifecycle = classify_vbts_records(records, on_date)
    _create_backup(csv_path, "otomatik_senkronizasyon")
    _write_records_atomic(csv_path, lifecycle.active)
    _write_sync_state(csv_path, lifecycle)
    activate_manual_vbts_source(csv_path)
    return lifecycle


@dataclass(frozen=True)
class DashboardVbtsBackupInfo:
    path: Path
    file_name: str
    created_at: str
    size_bytes: int
    record_count: int


def list_vbts_backups(csv_path: Path) -> tuple[DashboardVbtsBackupInfo, ...]:
    backup_dir = backup_directory_for(csv_path)
    if not backup_dir.exists():
        return ()

    items: list[DashboardVbtsBackupInfo] = []
    try:
        candidates = sorted(
            backup_dir.glob("vbts_kayitlari_*.csv"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in candidates:
            records = _read_records(path)
            modified = datetime.fromtimestamp(
                path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat(timespec="seconds")
            items.append(
                DashboardVbtsBackupInfo(
                    path=path,
                    file_name=path.name,
                    created_at=modified,
                    size_bytes=path.stat().st_size,
                    record_count=len(records),
                )
            )
    except OSError as exc:
        raise DashboardVbtsManagerError(
            f"VBTS yedekleri listelenemedi: {exc}"
        ) from exc
    return tuple(items)


def inspect_vbts_backup(
    csv_path: Path,
    backup_path: Path,
    on_date: date | None = None,
) -> tuple[
    tuple[DashboardVbtsRecord, ...],
    DashboardVbtsLifecycle,
]:
    backup_dir = backup_directory_for(csv_path).resolve()
    candidate = backup_path.resolve()

    if candidate.parent != backup_dir:
        raise DashboardVbtsManagerError(
            "Seçilen VBTS yedeği izin verilen yedek klasöründe değildir."
        )
    if not candidate.exists() or not candidate.is_file():
        raise DashboardVbtsManagerError("Seçilen VBTS yedeği bulunamadı.")
    if not candidate.name.startswith("vbts_kayitlari_"):
        raise DashboardVbtsManagerError(
            "Yalnızca VBTS kayıt arşivi yedeği geri yüklenebilir."
        )

    verify_backup_integrity(csv_path, candidate)
    records = _read_records(candidate)
    if not records:
        raise DashboardVbtsManagerError(
            "Boş VBTS yedeği geri yüklenemez."
        )
    return records, classify_vbts_records(records, on_date)


def restore_vbts_backup(
    csv_path: Path,
    backup_path: Path,
    on_date: date | None = None,
) -> tuple[DashboardVbtsRecord, ...]:
    records, _ = inspect_vbts_backup(csv_path, backup_path, on_date)
    registry_path = registry_path_for(csv_path)

    _create_backup(registry_path, "geri_yukleme_oncesi")
    _create_backup(csv_path, "geri_yukleme_oncesi")
    _write_records_atomic(registry_path, records)
    lifecycle = sync_active_vbts_csv(csv_path, records, on_date)
    _write_sync_state(csv_path, lifecycle)
    activate_manual_vbts_source(csv_path)
    _append_audit(
        csv_path,
        action="YEDEK_GERI_YUKLENDI",
        detail=(
            f"{backup_path.name} yedeğinden "
            f"{len(records)} VBTS kaydı geri yüklendi."
        ),
    )
    return records


def read_audit_events(
    csv_path: Path,
    limit: int = 50,
) -> tuple[dict[str, object], ...]:
    if limit < 1 or limit > 500:
        raise DashboardVbtsManagerError(
            "Denetim günlüğü kayıt sınırı 1 ile 500 arasında olmalıdır."
        )

    path = audit_log_path_for(csv_path)
    if not path.exists():
        return ()

    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DashboardVbtsManagerError(
            f"VBTS denetim günlüğü okunamadı: {exc}"
        ) from exc

    events: list[dict[str, object]] = []
    for line in reversed(raw_lines):
        cleaned = line.strip()
        if not cleaned:
            continue
        try:
            value = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise DashboardVbtsManagerError(
                "VBTS denetim günlüğü bozuk."
            ) from exc
        if not isinstance(value, dict):
            raise DashboardVbtsManagerError(
                "VBTS denetim günlüğü geçersiz."
            )
        events.append(value)
        if len(events) >= limit:
            break
    return tuple(events)


def audit_display_rows(
    events: tuple[dict[str, object], ...],
) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "Zaman (UTC)": str(event.get("timestamp_utc") or "—"),
            "İşlem": str(event.get("action") or "—"),
            "Açıklama": str(event.get("detail") or "—"),
            "Kayıt anahtarı": str(event.get("record_key") or "—"),
        }
        for event in events
    )


BACKUP_MANIFEST_NAME = "vbts_yedek_manifest.json"


@dataclass(frozen=True)
class DashboardVbtsHealthReport:
    healthy: bool
    registry_status: str
    active_csv_status: str
    backup_status: str
    audit_status: str
    backup_count: int
    audit_event_count: int
    messages: tuple[str, ...]


def backup_manifest_path_for(csv_path: Path) -> Path:
    return backup_directory_for(csv_path) / BACKUP_MANIFEST_NAME


def _sha256_for_path(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise DashboardVbtsManagerError(
            f"SHA-256 hesaplanamadı: {exc}"
        ) from exc
    return digest.hexdigest()


def _load_backup_manifest(csv_path: Path) -> dict[str, dict[str, object]]:
    path = backup_manifest_path_for(csv_path)
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DashboardVbtsManagerError(
            "VBTS yedek manifest dosyası bozuk."
        ) from exc
    if not isinstance(value, dict):
        raise DashboardVbtsManagerError(
            "VBTS yedek manifest dosyası geçersiz."
        )
    manifest: dict[str, dict[str, object]] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, dict):
            raise DashboardVbtsManagerError(
                "VBTS yedek manifest girdisi geçersiz."
            )
        manifest[key] = item
    return manifest


def _write_backup_manifest(
    csv_path: Path,
    manifest: dict[str, dict[str, object]],
) -> None:
    path = backup_manifest_path_for(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    try:
        temp_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(path)
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        raise DashboardVbtsManagerError(
            f"VBTS yedek manifesti yazılamadı: {exc}"
        ) from exc


def register_backup_integrity(
    csv_path: Path,
    backup_path: Path,
) -> None:
    manifest = _load_backup_manifest(csv_path)
    manifest[backup_path.name] = {
        "sha256": _sha256_for_path(backup_path),
        "size_bytes": backup_path.stat().st_size,
        "registered_at_utc": _utc_now_text(),
    }
    _write_backup_manifest(csv_path, manifest)


def verify_backup_integrity(
    csv_path: Path,
    backup_path: Path,
) -> bool:
    manifest = _load_backup_manifest(csv_path)
    item = manifest.get(backup_path.name)
    if item is None:
        raise DashboardVbtsManagerError(
            "Seçilen VBTS yedeği manifestte kayıtlı değildir."
        )
    expected = str(item.get("sha256") or "")
    if not expected:
        raise DashboardVbtsManagerError(
            "Seçilen VBTS yedeğinin SHA-256 değeri eksiktir."
        )
    actual = _sha256_for_path(backup_path)
    if actual != expected:
        raise DashboardVbtsManagerError(
            "VBTS yedeği bütünlük doğrulamasını geçemedi."
        )
    return True


def migrate_existing_backups_to_manifest(csv_path: Path) -> int:
    backup_dir = backup_directory_for(csv_path)
    if not backup_dir.exists():
        return 0

    manifest = _load_backup_manifest(csv_path)
    added = 0
    for path in backup_dir.glob("*.csv"):
        if path.name not in manifest:
            manifest[path.name] = {
                "sha256": _sha256_for_path(path),
                "size_bytes": path.stat().st_size,
                "registered_at_utc": _utc_now_text(),
            }
            added += 1
    if added:
        _write_backup_manifest(csv_path, manifest)
    return added


def prune_vbts_backups(
    csv_path: Path,
    *,
    keep_latest: int = 20,
) -> tuple[Path, ...]:
    if keep_latest < 1 or keep_latest > 500:
        raise DashboardVbtsManagerError(
            "Saklanacak yedek sayısı 1 ile 500 arasında olmalıdır."
        )

    backup_dir = backup_directory_for(csv_path)
    if not backup_dir.exists():
        return ()

    try:
        candidates = sorted(
            (
                path
                for path in backup_dir.glob("*.csv")
                if path.is_file()
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError as exc:
        raise DashboardVbtsManagerError(
            f"VBTS yedekleri sıralanamadı: {exc}"
        ) from exc

    removed = tuple(candidates[keep_latest:])
    if not removed:
        return ()

    manifest = _load_backup_manifest(csv_path)
    for path in removed:
        try:
            path.unlink()
        except OSError as exc:
            raise DashboardVbtsManagerError(
                f"Eski VBTS yedeği silinemedi: {exc}"
            ) from exc
        manifest.pop(path.name, None)

    _write_backup_manifest(csv_path, manifest)
    _append_audit(
        csv_path,
        action="ESKI_YEDEKLER_TEMIZLENDI",
        detail=f"{len(removed)} eski VBTS yedeği temizlendi.",
    )
    return removed


def audit_events_csv_bytes(
    events: tuple[dict[str, object], ...],
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=(
            "timestamp_utc",
            "action",
            "detail",
            "record_key",
        ),
    )
    writer.writeheader()
    for event in events:
        writer.writerow(
            {
                "timestamp_utc": event.get("timestamp_utc") or "",
                "action": event.get("action") or "",
                "detail": event.get("detail") or "",
                "record_key": event.get("record_key") or "",
            }
        )
    return output.getvalue().encode("utf-8-sig")


def validate_vbts_system_health(
    csv_path: Path,
) -> DashboardVbtsHealthReport:
    messages: list[str] = []
    healthy = True

    registry_path = registry_path_for(csv_path)
    if registry_path.exists():
        try:
            registry_records = _read_records(registry_path)
            registry_status = f"Sağlıklı · {len(registry_records)} kayıt"
        except DashboardVbtsManagerError as exc:
            registry_status = "Bozuk"
            messages.append(str(exc))
            healthy = False
    else:
        registry_records = ()
        registry_status = "Yok"

    if csv_path.exists():
        try:
            active_records = _read_records(csv_path)
            active_csv_status = f"Sağlıklı · {len(active_records)} aktif kayıt"
            lifecycle = classify_vbts_records(registry_records)
            if tuple(active_records) != tuple(lifecycle.active):
                active_csv_status = "Arşivle uyumsuz"
                messages.append(
                    "Aktif VBTS CSV ile kayıt arşivi senkronize değildir."
                )
                healthy = False
        except DashboardVbtsManagerError as exc:
            active_csv_status = "Bozuk"
            messages.append(str(exc))
            healthy = False
    else:
        active_csv_status = "Yok"
        if any(record.status() == STATUS_ACTIVE for record in registry_records):
            messages.append(
                "Aktif kayıt bulunduğu hâlde vbts_guncel.csv mevcut değildir."
            )
            healthy = False

    try:
        migrate_existing_backups_to_manifest(csv_path)
        backups = tuple(
            path
            for path in backup_directory_for(csv_path).glob("*.csv")
            if path.is_file()
        )
        for path in backups:
            verify_backup_integrity(csv_path, path)
        backup_status = f"Sağlıklı · {len(backups)} yedek"
    except DashboardVbtsManagerError as exc:
        backups = ()
        backup_status = "Bütünlük hatası"
        messages.append(str(exc))
        healthy = False

    try:
        events = read_audit_events(csv_path, limit=500)
        audit_status = f"Sağlıklı · {len(events)} işlem"
    except DashboardVbtsManagerError as exc:
        events = ()
        audit_status = "Bozuk"
        messages.append(str(exc))
        healthy = False

    return DashboardVbtsHealthReport(
        healthy=healthy,
        registry_status=registry_status,
        active_csv_status=active_csv_status,
        backup_status=backup_status,
        audit_status=audit_status,
        backup_count=len(backups),
        audit_event_count=len(events),
        messages=tuple(messages),
    )
