from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib import error, request
from urllib.parse import quote


MAX_IMAGE_BYTES = 10 * 1024 * 1024
SUPPORTED_IMAGE_TYPES: dict[str, tuple[str, ...]] = {
    "image/png": (".png",),
    "image/jpeg": (".jpg", ".jpeg"),
}


class MarketContextImageError(ValueError):
    """Seans öncesi bağlam görsel girdisi güvenle işlenemedi."""


class MarketContextImageExtractionError(RuntimeError):
    """Görselden metin çıkarma işlemi tamamlanamadı."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = bool(retryable)


@dataclass(frozen=True, slots=True)
class ValidatedMarketContextImage:
    original_name: str
    safe_name: str
    mime_type: str
    extension: str
    data: bytes
    sha256: str

    @property
    def size_bytes(self) -> int:
        return len(self.data)


@dataclass(frozen=True, slots=True)
class ArchivedMarketContextImage:
    image: ValidatedMarketContextImage
    file_path: Path
    metadata_path: Path
    archived_at: datetime
    reused_existing: bool


@dataclass(frozen=True, slots=True)
class ImageTextExtractionResult:
    provider: str
    model: str
    text: str
    elapsed_seconds: float


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]
NowProvider = Callable[[], datetime]


def _safe_filename(value: str, extension: str) -> str:
    raw = Path(str(value or "gorsel")).name
    stem = Path(raw).stem
    stem = re.sub(r"[^A-Za-z0-9ÇĞİÖŞÜçğıöşü._-]+", "-", stem).strip("-._")
    if not stem:
        stem = "gorsel"
    return f"{stem[:80]}{extension}"


def validate_market_context_image(
    *,
    filename: str,
    mime_type: str,
    data: bytes,
    maximum_bytes: int = MAX_IMAGE_BYTES,
) -> ValidatedMarketContextImage:
    if not isinstance(data, (bytes, bytearray)):
        raise MarketContextImageError("Görsel verisi bayt biçiminde olmalıdır.")
    image_bytes = bytes(data)
    if not image_bytes:
        raise MarketContextImageError("Yüklenen görsel boş.")
    if len(image_bytes) > int(maximum_bytes):
        raise MarketContextImageError(
            f"Görsel en fazla {int(maximum_bytes) // (1024 * 1024)} MB olabilir."
        )

    normalized_mime = str(mime_type or "").strip().lower()
    if normalized_mime not in SUPPORTED_IMAGE_TYPES:
        raise MarketContextImageError(
            "Yalnızca JPG, JPEG veya PNG görseller desteklenir."
        )

    suffix = Path(str(filename or "")).suffix.lower()
    allowed_suffixes = SUPPORTED_IMAGE_TYPES[normalized_mime]
    if suffix not in allowed_suffixes:
        raise MarketContextImageError(
            "Dosya uzantısı ile görsel MIME türü birbiriyle uyumlu değil."
        )

    # Dosya imzası kontrolü, yalnız uzantı/MIME bilgisine güvenilmesini önler.
    if normalized_mime == "image/png" and not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise MarketContextImageError("PNG dosya imzası doğrulanamadı.")
    if normalized_mime == "image/jpeg" and not image_bytes.startswith(b"\xff\xd8\xff"):
        raise MarketContextImageError("JPEG dosya imzası doğrulanamadı.")

    digest = hashlib.sha256(image_bytes).hexdigest()
    extension = ".png" if normalized_mime == "image/png" else ".jpg"
    return ValidatedMarketContextImage(
        original_name=Path(str(filename or "gorsel")).name,
        safe_name=_safe_filename(filename, extension),
        mime_type=normalized_mime,
        extension=extension,
        data=image_bytes,
        sha256=digest,
    )


class MarketContextImageArchive:
    def __init__(
        self,
        root: str | Path,
        *,
        now_provider: NowProvider | None = None,
    ) -> None:
        self.root = Path(root)
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def archive(self, image: ValidatedMarketContextImage) -> ArchivedMarketContextImage:
        now = self._now_provider()
        if now.tzinfo is None or now.utcoffset() is None:
            raise MarketContextImageError("Arşiv zamanı saat dilimi içermelidir.")

        day_dir = self.root / now.date().isoformat()
        day_dir.mkdir(parents=True, exist_ok=True)
        base_name = f"{image.sha256[:16]}-{Path(image.safe_name).stem}"
        file_path = day_dir / f"{base_name}{image.extension}"
        metadata_path = day_dir / f"{base_name}.json"
        reused = file_path.exists()

        if reused:
            if hashlib.sha256(file_path.read_bytes()).hexdigest() != image.sha256:
                raise MarketContextImageError(
                    "Arşivde aynı kimlikte farklı içerik bulundu; dosya korunarak işlem durduruldu."
                )
        else:
            file_path.write_bytes(image.data)

        metadata = {
            "schema_version": 1,
            "sha256": image.sha256,
            "original_name": image.original_name,
            "stored_name": file_path.name,
            "mime_type": image.mime_type,
            "size_bytes": image.size_bytes,
            "archived_at": now.isoformat(),
            "review": {
                "approved": False,
                "approved_text_sha256": "",
                "approved_at": "",
            },
        }
        if metadata_path.exists():
            try:
                existing = json.loads(metadata_path.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    metadata["review"] = existing.get("review", metadata["review"])
                    metadata["archived_at"] = existing.get("archived_at", metadata["archived_at"])
            except (OSError, json.JSONDecodeError):
                pass
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        archived_at = datetime.fromisoformat(str(metadata["archived_at"]))
        return ArchivedMarketContextImage(
            image=image,
            file_path=file_path,
            metadata_path=metadata_path,
            archived_at=archived_at,
            reused_existing=reused,
        )

    def mark_review_approved(
        self,
        archived: ArchivedMarketContextImage,
        approved_text: str,
    ) -> None:
        normalized_text = str(approved_text or "").strip()
        if not normalized_text:
            raise MarketContextImageError("Onaylanan metin boş olamaz.")
        try:
            metadata = json.loads(archived.metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise MarketContextImageError("Görsel arşiv metadata kaydı okunamadı.") from exc
        now = self._now_provider()
        metadata["review"] = {
            "approved": True,
            "approved_text_sha256": hashlib.sha256(
                normalized_text.encode("utf-8")
            ).hexdigest(),
            "approved_at": now.isoformat(),
        }
        archived.metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def _default_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        status_code = int(exc.code)
        raise MarketContextImageExtractionError(
            f"Gemini görsel okuma HTTP hatası: {status_code}. {detail[:400]}",
            status_code=status_code,
            retryable=status_code in {429, 503},
        ) from exc
    except (error.URLError, TimeoutError) as exc:
        raise MarketContextImageExtractionError(
            f"Gemini görsel okuma bağlantı hatası: {exc}"
        ) from exc
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MarketContextImageExtractionError(
            "Gemini geçerli JSON yanıtı döndürmedi."
        ) from exc
    if not isinstance(result, dict):
        raise MarketContextImageExtractionError("Gemini yanıtı nesne biçiminde değil.")
    return result


def _extract_response_text(response: dict[str, Any]) -> str:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise MarketContextImageExtractionError("Gemini yanıtında metin adayı bulunamadı.")
    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [
        item.get("text", "")
        for item in parts
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    ]
    text = "".join(texts).strip()
    if not text:
        raise MarketContextImageExtractionError("Gemini görselden metin çıkaramadı.")
    # Model bazen salt metni kod bloğu içinde döndürebilir; sadece dış çiti kaldır.
    if text.startswith("```") and text.endswith("```"):
        text = re.sub(r"^```(?:text)?\s*", "", text, count=1, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text, count=1).strip()
    return text


class GeminiMarketContextImageExtractor:
    PROMPT = (
        "Bu görsel bir finans/piyasa ekran görüntüsü veya WhatsApp mesajı olabilir. "
        "Görselde okunabilen metni okuma sırasını ve satır ayrımlarını mümkün olduğunca "
        "koruyarak çıkar. Yorum, özet, yatırım görüşü, hedef fiyat veya görselde olmayan "
        "hiçbir bilgi ekleme. Okunamayan bölüm varsa [OKUNAMADI] yaz. Sadece çıkarılan "
        "metni döndür."
    )

    DEFAULT_RETRY_DELAYS_SECONDS = (2.0, 4.0, 8.0)

    def __init__(
        self,
        *,
        model: str | None = None,
        timeout_seconds: float | None = None,
        transport: Transport = _default_transport,
        retry_delays_seconds: tuple[float, ...] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        jitter_fn: Callable[[], float] | None = None,
    ) -> None:
        self.model = (
            model
            if model is not None
            else os.getenv("HISSE_ROBOTU_GEMINI_MODEL", "gemini-3.5-flash-lite")
        ).strip()
        self.timeout_seconds = (
            float(timeout_seconds)
            if timeout_seconds is not None
            else float(os.getenv("HISSE_ROBOTU_AI_TIMEOUT", "45"))
        )
        self.transport = transport
        self.retry_delays_seconds = (
            tuple(float(value) for value in retry_delays_seconds)
            if retry_delays_seconds is not None
            else self.DEFAULT_RETRY_DELAYS_SECONDS
        )
        if any(delay < 0 for delay in self.retry_delays_seconds):
            raise ValueError("Gemini yeniden deneme gecikmeleri negatif olamaz.")
        self.sleep_fn = sleep_fn
        # Deterministic bounded jitter without adding a random-module dependency:
        # time.monotonic's fractional part gives 0..0.35 s spread in production.
        self.jitter_fn = jitter_fn or (
            lambda: (time.monotonic() % 1.0) * 0.35
        )

    def _request_with_retry(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        attempt = 1
        max_attempts = 1 + len(self.retry_delays_seconds)

        while True:
            try:
                return self.transport(
                    url,
                    headers,
                    payload,
                    self.timeout_seconds,
                )
            except MarketContextImageExtractionError as exc:
                if not exc.retryable:
                    raise
                if attempt >= max_attempts:
                    status = (
                        f"HTTP {exc.status_code}"
                        if exc.status_code is not None
                        else "geçici servis hatası"
                    )
                    raise MarketContextImageExtractionError(
                        "Gemini görsel okuma geçici olarak kullanılamıyor "
                        f"({status}). {max_attempts} deneme başarısız. "
                        "Görsel arşivde korunuyor; metni manuel olarak "
                        "girebilir veya daha sonra yeniden deneyebilirsiniz.",
                        status_code=exc.status_code,
                        retryable=True,
                    ) from exc

                delay = self.retry_delays_seconds[attempt - 1]
                jitter = max(0.0, min(float(self.jitter_fn()), 0.35))
                self.sleep_fn(delay + jitter)
                attempt += 1

    def extract(self, image: ValidatedMarketContextImage) -> ImageTextExtractionResult:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise MarketContextImageExtractionError(
                "GEMINI_API_KEY tanımlı değil. Görsel arşivlendi; metni manuel olarak girebilirsiniz."
            )
        if not self.model:
            raise MarketContextImageExtractionError("Gemini model adı tanımlı değil.")

        encoded = base64.b64encode(image.data).decode("ascii")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{quote(self.model, safe='')}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": image.mime_type,
                                "data": encoded,
                            }
                        },
                        {"text": self.PROMPT},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 8192,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }

        started = time.perf_counter()
        response = self._request_with_retry(
            url=url,
            headers=headers,
            payload=payload,
        )
        text = _extract_response_text(response)
        return ImageTextExtractionResult(
            provider="gemini",
            model=self.model,
            text=text,
            elapsed_seconds=round(time.perf_counter() - started, 4),
        )
