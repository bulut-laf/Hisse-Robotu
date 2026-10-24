from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib import error, request

DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_TIMEOUT_SECONDS = 45.0
MAX_PDF_BYTES = 15 * 1024 * 1024
MAX_EXTRACTED_CHARS = 100_000
RETRY_DELAYS_SECONDS = (2.0, 4.0, 8.0)
MAX_JITTER_SECONDS = 0.35


class PdfImageFallbackError(RuntimeError):
    """Görüntü tabanlı PDF metni güvenle çıkarılamadığında kullanılır."""


class PdfImageFallbackProviderError(PdfImageFallbackError):
    def __init__(self, message: str, *, status_code: int | None = None, retriable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retriable = retriable


@dataclass(frozen=True, slots=True)
class PdfImageFallbackResult:
    ok: bool
    status: str
    text: str
    provider: str
    model: str
    elapsed_seconds: float
    digest: str
    error: str = ""


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]
SleepFunc = Callable[[float], None]
JitterFunc = Callable[[float, float], float]


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
        retriable = exc.code in (429, 503)
        raise PdfImageFallbackProviderError(
            f"Gemini PDF okuma HTTP hatası: {exc.code}. {detail[:500]}",
            status_code=exc.code,
            retriable=retriable,
        ) from exc
    except (error.URLError, TimeoutError) as exc:
        raise PdfImageFallbackProviderError(
            f"Gemini PDF okuma bağlantı hatası: {exc}",
            retriable=True,
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PdfImageFallbackProviderError(
            "Gemini PDF okuma geçerli JSON yanıtı döndürmedi."
        ) from exc
    if not isinstance(data, dict):
        raise PdfImageFallbackProviderError(
            "Gemini PDF okuma yanıtı nesne biçiminde değil."
        )
    return data


def _validate_pdf_bytes(pdf_bytes: bytes) -> bytes:
    if not isinstance(pdf_bytes, (bytes, bytearray)):
        raise PdfImageFallbackError("PDF içeriği bayt biçiminde olmalıdır.")
    data = bytes(pdf_bytes)
    if not data:
        raise PdfImageFallbackError("PDF dosyası boş.")
    if len(data) > MAX_PDF_BYTES:
        raise PdfImageFallbackError(
            f"Görüntü tabanlı PDF fallback için dosya en fazla {MAX_PDF_BYTES // (1024 * 1024)} MB olabilir."
        )
    if not data.lstrip().startswith(b"%PDF-"):
        raise PdfImageFallbackError("Dosya geçerli bir PDF imzasıyla başlamıyor.")
    return data


def _prompt(filename: str) -> str:
    safe_name = (filename or "taranmis-belge.pdf").strip()[:180]
    return (
        "Bu PDF, Seans Öncesi Bağlam ekranında kullanılacak bir piyasa/finans bülteni olabilir. "
        "Belgedeki okunabilir metni mümkün olduğunca sadık biçimde çıkar. Başlıkları, madde işaretlerini, "
        "sayısal seviyeleri, yüzdeleri, tarihleri, şirket/sektör adlarını ve tablo içeriğini koru. "
        "Görsel veya taranmış sayfalardaki yazıları da oku. Okunamayan bölümü uydurma; [OKUNAMADI] yaz. "
        "Belgeyi yorumlama, özetleme, yatırım tavsiyesi verme veya eksik bilgi tamamlama. "
        "AL/SAT, hedef, stop, teknik skor ya da fiyat yönü üretme. Yalnız belgeden çıkarılabilen metni düz metin olarak döndür. "
        f"Dosya adı: {safe_name}"
    )


def _response_text(response: dict[str, Any]) -> str:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise PdfImageFallbackProviderError("Gemini PDF yanıtında aday çıktı bulunamadı.")
    first = candidates[0]
    if not isinstance(first, dict):
        raise PdfImageFallbackProviderError("Gemini PDF yanıtındaki aday çıktı geçersiz.")
    content = first.get("content")
    if not isinstance(content, dict):
        raise PdfImageFallbackProviderError("Gemini PDF yanıtında içerik bulunamadı.")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise PdfImageFallbackProviderError("Gemini PDF yanıtında metin parçaları bulunamadı.")
    texts = [
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ]
    text = "".join(texts).strip()
    if not text:
        raise PdfImageFallbackProviderError("Gemini PDF'den boş metin döndürdü.")
    if len(text) > MAX_EXTRACTED_CHARS:
        text = text[:MAX_EXTRACTED_CHARS].rstrip() + "\n[METIN UZUNLUK SINIRI NEDENIYLE KESILDI]"
    return text


def _call_with_retry(
    call: Callable[[], dict[str, Any]],
    *,
    sleep_func: SleepFunc,
    jitter_func: JitterFunc,
) -> dict[str, Any]:
    attempt = 0
    while True:
        try:
            return call()
        except PdfImageFallbackProviderError as exc:
            if not exc.retriable or attempt >= len(RETRY_DELAYS_SECONDS):
                raise
            delay = RETRY_DELAYS_SECONDS[attempt] + max(
                0.0,
                min(MAX_JITTER_SECONDS, float(jitter_func(0.0, MAX_JITTER_SECONDS))),
            )
            sleep_func(delay)
            attempt += 1


def extract_scanned_pdf_text(
    pdf_bytes: bytes,
    *,
    filename: str = "",
    transport: Transport = _default_transport,
    sleep_func: SleepFunc = time.sleep,
    jitter_func: JitterFunc = random.uniform,
    timeout_seconds: float | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> PdfImageFallbackResult:
    """PDF'yi Gemini'nin yerel PDF görsel anlayışıyla yalnız metin çıkarımı için işler."""

    data = _validate_pdf_bytes(pdf_bytes)
    digest = hashlib.sha256(data).hexdigest()
    selected_model = (model or os.getenv("HISSE_ROBOTU_GEMINI_MODEL", DEFAULT_MODEL)).strip()
    selected_key = (api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")).strip()
    selected_timeout = float(
        timeout_seconds
        if timeout_seconds is not None
        else os.getenv("HISSE_ROBOTU_AI_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS))
    )

    if not selected_key:
        raise PdfImageFallbackError("GEMINI_API_KEY tanımlı değil.")
    if not selected_model:
        raise PdfImageFallbackError("Gemini model adı tanımlı değil.")
    if selected_timeout <= 0:
        raise PdfImageFallbackError("PDF okuma zaman aşımı pozitif olmalıdır.")

    encoded = base64.b64encode(data).decode("ascii")
    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": _prompt(filename)},
                    {
                        "inlineData": {
                            "mimeType": "application/pdf",
                            "data": encoded,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
        },
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": selected_key,
    }
    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{selected_model}:generateContent"
    )

    started = time.perf_counter()
    try:
        response = _call_with_retry(
            lambda: transport(url, headers, payload, selected_timeout),
            sleep_func=sleep_func,
            jitter_func=jitter_func,
        )
        text = _response_text(response)
    except PdfImageFallbackError as exc:
        return PdfImageFallbackResult(
            ok=False,
            status="provider_error",
            text="",
            provider="gemini",
            model=selected_model,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            digest=digest,
            error=str(exc),
        )

    return PdfImageFallbackResult(
        ok=True,
        status="accepted",
        text=text,
        provider="gemini",
        model=selected_model,
        elapsed_seconds=round(time.perf_counter() - started, 3),
        digest=digest,
        error="",
    )
