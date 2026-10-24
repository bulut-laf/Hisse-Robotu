from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

from .backtest_history import (
    METADATA_DOSYASI,
    BacktestHistoryError,
    BacktestHistoryRecord,
    BacktestHistoryStore,
)

YEDEK_SURUMU = 1
MANIFEST_DOSYASI = "manifest.json"
KAYITLAR_KLASORU = "kayitlar"
MAKSIMUM_YEDEK_BOYUTU = 128 * 1024 * 1024
MAKSIMUM_DOSYA_SAYISI = 10_000


class BacktestHistoryBackupError(RuntimeError):
    """Analiz geçmişi yedeği üretilemediğinde veya okunamadığında oluşur."""


@dataclass(frozen=True)
class BackupPreview:
    """Geri yükleme öncesi doğrulanmış ZIP yedeği özeti."""

    toplam_kayit: int
    yeni_kayit: int
    zaten_mevcut: int
    toplam_dosya: int
    toplam_boyut: int
    kayit_kimlikleri: tuple[str, ...]


@dataclass(frozen=True)
class RestoreResult:
    """Başarılı geri yükleme işleminin sonucu."""

    geri_yuklenen: int
    atlanan_ayni_kayit: int
    toplam_kayit: int


@dataclass(frozen=True)
class _ValidatedRecord:
    record: BacktestHistoryRecord
    files: tuple[tuple[str, bytes], ...]
    exists_identically: bool


@dataclass(frozen=True)
class _ValidatedBackup:
    records: tuple[_ValidatedRecord, ...]
    total_file_count: int
    total_size: int


class BacktestHistoryBackupService:
    """Analiz geçmişini güvenli ZIP yedeğine dönüştürür ve geri yükler."""

    def __init__(self, store: BacktestHistoryStore) -> None:
        if not isinstance(store, BacktestHistoryStore):
            raise TypeError("Yedekleme servisi BacktestHistoryStore gerektirir.")
        self.store = store

    def yedek_olustur(
        self,
        kayit_kimlikleri: Iterable[str] | None = None,
    ) -> bytes:
        records = self._records_for_backup(kayit_kimlikleri)
        output = io.BytesIO()
        manifest_records: list[dict[str, object]] = []

        with zipfile.ZipFile(
            output,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for record in records:
                record_files: list[dict[str, object]] = []
                metadata = json.dumps(
                    record.sozluk(),
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8")
                metadata_path = self._archive_path(
                    record.kayit_kimligi,
                    METADATA_DOSYASI,
                )
                archive.writestr(metadata_path, metadata)
                record_files.append(_manifest_file(metadata_path, metadata))

                for artifact in record.dosyalar:
                    data = self.store.dosya_baytlari(record, artifact.tur)
                    archive_path = self._archive_path(
                        record.kayit_kimligi,
                        artifact.goreli_yol,
                    )
                    archive.writestr(archive_path, data)
                    record_files.append(_manifest_file(archive_path, data))

                manifest_records.append(
                    {
                        "kayit_kimligi": record.kayit_kimligi,
                        "dosyalar": record_files,
                    }
                )

            manifest = {
                "surum": YEDEK_SURUMU,
                "uygulama": "Hisse Robotu",
                "kayit_sayisi": len(records),
                "kayitlar": manifest_records,
            }
            archive.writestr(
                MANIFEST_DOSYASI,
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
            )

        result = output.getvalue()
        if len(result) > MAKSIMUM_YEDEK_BOYUTU:
            raise BacktestHistoryBackupError(
                "Analiz geçmişi yedeği izin verilen boyutu aşıyor."
            )
        return result

    def yedegi_incele(self, zip_bytes: bytes) -> BackupPreview:
        validated = self._validate_backup(zip_bytes)
        return BackupPreview(
            toplam_kayit=len(validated.records),
            yeni_kayit=sum(
                not item.exists_identically for item in validated.records
            ),
            zaten_mevcut=sum(
                item.exists_identically for item in validated.records
            ),
            toplam_dosya=validated.total_file_count,
            toplam_boyut=validated.total_size,
            kayit_kimlikleri=tuple(
                item.record.kayit_kimligi for item in validated.records
            ),
        )

    def yedegi_geri_yukle(self, zip_bytes: bytes) -> RestoreResult:
        validated = self._validate_backup(zip_bytes)
        new_records = tuple(
            item for item in validated.records if not item.exists_identically
        )
        if not new_records:
            return RestoreResult(
                geri_yuklenen=0,
                atlanan_ayni_kayit=len(validated.records),
                toplam_kayit=len(validated.records),
            )

        root = self.store.kok_klasor
        root.mkdir(parents=True, exist_ok=True)
        created: list[Path] = []
        staging_root = Path(
            tempfile.mkdtemp(prefix=".hisse_robotu_restore_", dir=root.parent)
        )
        try:
            for item in new_records:
                stage_record = staging_root / item.record.kayit_kimligi
                stage_record.mkdir(parents=True, exist_ok=False)
                for relative_name, data in item.files:
                    target = stage_record / relative_name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)

            for item in new_records:
                source = staging_root / item.record.kayit_kimligi
                target = root / item.record.kayit_kimligi
                if target.exists():
                    raise BacktestHistoryBackupError(
                        "Geri yükleme sırasında kayıt çakışması oluştu."
                    )
                source.replace(target)
                created.append(target)
        except (OSError, BacktestHistoryBackupError) as error:
            for path in reversed(created):
                shutil.rmtree(path, ignore_errors=True)
            if isinstance(error, BacktestHistoryBackupError):
                raise
            raise BacktestHistoryBackupError(
                "Analiz geçmişi yedeği geri yüklenemedi."
            ) from error
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

        return RestoreResult(
            geri_yuklenen=len(new_records),
            atlanan_ayni_kayit=len(validated.records) - len(new_records),
            toplam_kayit=len(validated.records),
        )

    def _records_for_backup(
        self,
        record_ids: Iterable[str] | None,
    ) -> tuple[BacktestHistoryRecord, ...]:
        if record_ids is None:
            return self.store.kayitlari_listele(limit=10_000)
        if isinstance(record_ids, (str, bytes)):
            raise TypeError("Yedeklenecek kayıt kimlikleri koleksiyon olmalıdır.")

        unique_ids = tuple(dict.fromkeys(record_ids))
        return tuple(self.store.kayit_getir(record_id) for record_id in unique_ids)

    def _validate_backup(self, zip_bytes: bytes) -> _ValidatedBackup:
        if not isinstance(zip_bytes, (bytes, bytearray)):
            raise TypeError("Analiz geçmişi yedeği bayt olmalıdır.")
        if not zip_bytes:
            raise BacktestHistoryBackupError("Analiz geçmişi yedeği boş.")
        if len(zip_bytes) > MAKSIMUM_YEDEK_BOYUTU:
            raise BacktestHistoryBackupError(
                "Analiz geçmişi yedeği izin verilen boyutu aşıyor."
            )

        try:
            archive = zipfile.ZipFile(io.BytesIO(bytes(zip_bytes)), mode="r")
        except (OSError, zipfile.BadZipFile) as error:
            raise BacktestHistoryBackupError(
                "Geçerli bir analiz geçmişi ZIP yedeği seçin."
            ) from error

        with archive:
            infos = archive.infolist()
            if len(infos) > MAKSIMUM_DOSYA_SAYISI:
                raise BacktestHistoryBackupError(
                    "Analiz geçmişi yedeğinde çok fazla dosya var."
                )
            self._validate_archive_members(infos)
            total_size = sum(info.file_size for info in infos)
            if total_size > MAKSIMUM_YEDEK_BOYUTU:
                raise BacktestHistoryBackupError(
                    "Açılmış analiz geçmişi yedeği izin verilen boyutu aşıyor."
                )
            try:
                manifest_raw = archive.read(MANIFEST_DOSYASI)
                manifest = json.loads(manifest_raw.decode("utf-8"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise BacktestHistoryBackupError(
                    "Analiz geçmişi yedek manifesti okunamadı."
                ) from error

            manifest_records = self._validate_manifest(manifest)
            expected_paths = {MANIFEST_DOSYASI}
            validated_records: list[_ValidatedRecord] = []
            for manifest_record in manifest_records:
                validated = self._validate_manifest_record(
                    archive,
                    manifest_record,
                )
                validated_records.append(validated)
                for relative_name, _ in validated.files:
                    expected_paths.add(
                        self._archive_path(
                            validated.record.kayit_kimligi,
                            relative_name,
                        )
                    )

            actual_paths = {info.filename for info in infos if not info.is_dir()}
            if actual_paths != expected_paths:
                raise BacktestHistoryBackupError(
                    "Analiz geçmişi yedeği beklenmeyen veya eksik dosya içeriyor."
                )

            return _ValidatedBackup(
                records=tuple(validated_records),
                total_file_count=len(actual_paths) - 1,
                total_size=total_size,
            )

    def _validate_archive_members(
        self,
        infos: list[zipfile.ZipInfo],
    ) -> None:
        seen: set[str] = set()
        for info in infos:
            path = PurePosixPath(info.filename)
            if (
                not info.filename
                or info.filename in seen
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in info.filename
                or ":" in info.filename
            ):
                raise BacktestHistoryBackupError(
                    "Analiz geçmişi yedeği güvenli olmayan dosya yolu içeriyor."
                )
            seen.add(info.filename)
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(unix_mode):
                raise BacktestHistoryBackupError(
                    "Analiz geçmişi yedeği bağlantı dosyası içeremez."
                )

    def _validate_manifest(self, manifest: object) -> list[dict[str, object]]:
        if not isinstance(manifest, dict):
            raise BacktestHistoryBackupError("Analiz geçmişi manifesti geçersiz.")
        if int(manifest.get("surum", 0)) != YEDEK_SURUMU:
            raise BacktestHistoryBackupError(
                "Desteklenmeyen analiz geçmişi yedek sürümü."
            )
        raw_records = manifest.get("kayitlar")
        if not isinstance(raw_records, list):
            raise BacktestHistoryBackupError("Yedek kayıt listesi geçersiz.")
        if int(manifest.get("kayit_sayisi", -1)) != len(raw_records):
            raise BacktestHistoryBackupError("Yedek kayıt sayısı uyuşmuyor.")

        result: list[dict[str, object]] = []
        seen_ids: set[str] = set()
        for raw_record in raw_records:
            if not isinstance(raw_record, dict):
                raise BacktestHistoryBackupError("Yedek kayıt girdisi geçersiz.")
            record_id = str(raw_record.get("kayit_kimligi", ""))
            if (
                not record_id
                or record_id in seen_ids
                or re.fullmatch(r"[A-Za-z0-9_-]+", record_id) is None
            ):
                raise BacktestHistoryBackupError(
                    "Yedek kayıt kimliği geçersiz veya yinelenmiş."
                )
            seen_ids.add(record_id)
            result.append(raw_record)
        return result

    def _validate_manifest_record(
        self,
        archive: zipfile.ZipFile,
        manifest_record: dict[str, object],
    ) -> _ValidatedRecord:
        record_id = str(manifest_record["kayit_kimligi"])
        raw_files = manifest_record.get("dosyalar")
        if not isinstance(raw_files, list) or not raw_files:
            raise BacktestHistoryBackupError("Yedek kayıt dosya listesi geçersiz.")

        files_by_archive_path: dict[str, bytes] = {}
        for raw_file in raw_files:
            if not isinstance(raw_file, dict):
                raise BacktestHistoryBackupError("Yedek dosya girdisi geçersiz.")
            archive_path = str(raw_file.get("yol", ""))
            expected_size = int(raw_file.get("boyut", -1))
            expected_hash = str(raw_file.get("sha256", ""))
            try:
                data = archive.read(archive_path)
            except KeyError as error:
                raise BacktestHistoryBackupError(
                    "Yedek manifestinde belirtilen dosya bulunamadı."
                ) from error
            if len(data) != expected_size or _sha256(data) != expected_hash:
                raise BacktestHistoryBackupError(
                    "Analiz geçmişi yedek dosyası doğrulanamadı."
                )
            files_by_archive_path[archive_path] = data

        metadata_path = self._archive_path(record_id, METADATA_DOSYASI)
        metadata_data = files_by_archive_path.get(metadata_path)
        if metadata_data is None:
            raise BacktestHistoryBackupError("Yedek kayıt metadata dosyası eksik.")
        try:
            record = BacktestHistoryRecord.sozlukten(
                json.loads(metadata_data.decode("utf-8"))
            )
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as error:
            raise BacktestHistoryBackupError(
                "Yedek kayıt metadata bilgisi geçersiz."
            ) from error
        if record.kayit_kimligi != record_id:
            raise BacktestHistoryBackupError(
                "Yedek klasörü ile kayıt kimliği uyuşmuyor."
            )

        expected_record_paths = {metadata_path}
        relative_files: list[tuple[str, bytes]] = [(METADATA_DOSYASI, metadata_data)]
        for artifact in record.dosyalar:
            if PurePosixPath(artifact.goreli_yol).name != artifact.goreli_yol:
                raise BacktestHistoryBackupError(
                    "Yedek rapor dosya yolu geçersiz."
                )
            archive_path = self._archive_path(record_id, artifact.goreli_yol)
            data = files_by_archive_path.get(archive_path)
            if data is None:
                raise BacktestHistoryBackupError(
                    "Yedek kayıt rapor dosyası eksik."
                )
            expected_record_paths.add(archive_path)
            relative_files.append((artifact.goreli_yol, data))

        if set(files_by_archive_path) != expected_record_paths:
            raise BacktestHistoryBackupError(
                "Yedek kayıt beklenmeyen dosya içeriyor."
            )

        exists_identically = self._existing_record_state(record, tuple(relative_files))
        return _ValidatedRecord(
            record=record,
            files=tuple(relative_files),
            exists_identically=exists_identically,
        )

    def _existing_record_state(
        self,
        record: BacktestHistoryRecord,
        files: tuple[tuple[str, bytes], ...],
    ) -> bool:
        target = self.store.kok_klasor / record.kayit_kimligi
        if target.is_symlink():
            raise BacktestHistoryBackupError(
                "Mevcut analiz geçmişi kayıt yolu geçersiz."
            )
        if not target.exists():
            return False
        if not target.is_dir():
            raise BacktestHistoryBackupError(
                "Mevcut analiz geçmişi kayıt yolu geçersiz."
            )
        for relative_name, expected in files:
            path = target / relative_name
            try:
                actual = path.read_bytes()
            except OSError as error:
                raise BacktestHistoryBackupError(
                    "Mevcut analiz geçmişi kaydı okunamadı."
                ) from error
            if actual != expected:
                raise BacktestHistoryBackupError(
                    "Aynı kimlikte farklı bir analiz geçmişi kaydı zaten var."
                )
        actual_files = {
            path.name for path in target.iterdir() if path.is_file()
        }
        expected_files = {relative_name for relative_name, _ in files}
        if actual_files != expected_files:
            raise BacktestHistoryBackupError(
                "Aynı kimlikte farklı bir analiz geçmişi kaydı zaten var."
            )
        return True

    @staticmethod
    def _archive_path(record_id: str, relative_name: str) -> str:
        return str(PurePosixPath(KAYITLAR_KLASORU, record_id, relative_name))


def _manifest_file(path: str, data: bytes) -> dict[str, object]:
    return {
        "yol": path,
        "boyut": len(data),
        "sha256": _sha256(data),
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
