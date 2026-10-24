from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib import error, request


class AIProviderError(RuntimeError):
    """AI sağlayıcı çağrısı güvenle tamamlanamadığında kullanılır."""


@dataclass(frozen=True, slots=True)
class AIProviderConfig:
    provider: str = "gemini"
    model: str = ""
    timeout_seconds: float = 45.0
    max_retries: int = 1

    @classmethod
    def from_environment(cls) -> "AIProviderConfig":
        provider = os.getenv("HISSE_ROBOTU_AI_PROVIDER", "gemini").strip().lower()
        if provider == "gemini":
            model = os.getenv("HISSE_ROBOTU_GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
        elif provider == "openai":
            model = os.getenv("HISSE_ROBOTU_OPENAI_MODEL", "gpt-5.6-luna").strip()
        else:
            model = ""
        return cls(
            provider=provider,
            model=model,
            timeout_seconds=float(os.getenv("HISSE_ROBOTU_AI_TIMEOUT", "45")),
            max_retries=int(os.getenv("HISSE_ROBOTU_AI_MAX_RETRIES", "1")),
        )


@dataclass(frozen=True, slots=True)
class AIProviderResult:
    provider: str
    model: str
    output: dict[str, Any]
    elapsed_seconds: float


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": ["string", "null"]},
        "positive_factors": {"type": "array", "items": {"type": "string"}},
        "risk_factors": {"type": "array", "items": {"type": "string"}},
        "stock_specific_risks": {"type": "array", "items": {"type": "string"}},
        "aligned_points": {"type": "array", "items": {"type": "string"}},
        "conflicting_points": {"type": "array", "items": {"type": "string"}},
        "watch_items": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "summary",
        "positive_factors",
        "risk_factors",
        "stock_specific_risks",
        "aligned_points",
        "conflicting_points",
        "watch_items",
    ],
    "additionalProperties": False,
}


def _default_transport(url, headers, payload, timeout):
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
        raise AIProviderError(f"AI sağlayıcı HTTP hatası: {exc.code}. {detail[:500]}") from exc
    except (error.URLError, TimeoutError) as exc:
        raise AIProviderError(f"AI sağlayıcı bağlantı hatası: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIProviderError("AI sağlayıcı geçerli JSON yanıtı döndürmedi.") from exc
    if not isinstance(data, dict):
        raise AIProviderError("AI sağlayıcı yanıtı nesne biçiminde değil.")
    return data


def _json_output_from_text(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIProviderError("AI modeli yapılandırılmış JSON çıktı üretmedi.") from exc
    if not isinstance(value, dict):
        raise AIProviderError("AI modeli JSON nesnesi yerine farklı bir değer döndürdü.")
    return value


def _gemini_output(response: dict[str, Any]) -> dict[str, Any]:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AIProviderError("Gemini yanıtında aday çıktı bulunamadı.")
    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [
        p.get("text", "")
        for p in parts
        if isinstance(p, dict) and isinstance(p.get("text"), str)
    ]
    text = "".join(texts).strip()
    if not text:
        raise AIProviderError("Gemini boş metin çıktısı döndürdü.")
    return _json_output_from_text(text)


def _openai_output(response: dict[str, Any]) -> dict[str, Any]:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return _json_output_from_text(direct.strip())
    output = response.get("output")
    if not isinstance(output, list):
        raise AIProviderError("OpenAI yanıtında output alanı bulunamadı.")
    texts = []
    for item in output:
        if not isinstance(item, dict):
            continue
        for part in item.get("content", []):
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                texts.append(part["text"])
    text = "".join(texts).strip()
    if not text:
        raise AIProviderError("OpenAI boş metin çıktısı döndürdü.")
    return _json_output_from_text(text)


def _call_with_retry(call, max_retries):
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return call()
        except AIProviderError as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(min(0.5 * (attempt + 1), 1.5))
    raise AIProviderError(str(last_error or "AI sağlayıcı çağrısı başarısız."))


class GeminiProvider:
    def __init__(self, config: AIProviderConfig, *, transport: Transport = _default_transport):
        self.config = config
        self.transport = transport

    def evaluate(self, prompt: str) -> AIProviderResult:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise AIProviderError("GEMINI_API_KEY tanımlı değil.")
        if not self.config.model:
            raise AIProviderError("Gemini model adı tanımlı değil.")
        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{self.config.model}:generateContent"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "responseJsonSchema": OUTPUT_SCHEMA,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }
        started = time.perf_counter()
        response = _call_with_retry(
            lambda: self.transport(
                url, headers, payload, self.config.timeout_seconds
            ),
            self.config.max_retries,
        )
        return AIProviderResult(
            provider="gemini",
            model=self.config.model,
            output=_gemini_output(response),
            elapsed_seconds=round(time.perf_counter() - started, 3),
        )


class OpenAIProvider:
    def __init__(self, config: AIProviderConfig, *, transport: Transport = _default_transport):
        self.config = config
        self.transport = transport

    def evaluate(self, prompt: str) -> AIProviderResult:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise AIProviderError("OPENAI_API_KEY tanımlı değil.")
        if not self.config.model:
            raise AIProviderError("OpenAI model adı tanımlı değil.")
        payload = {
            "model": self.config.model,
            "input": prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "market_context_evaluation",
                    "schema": OUTPUT_SCHEMA,
                    "strict": True,
                }
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        started = time.perf_counter()
        response = _call_with_retry(
            lambda: self.transport(
                "https://api.openai.com/v1/responses",
                headers,
                payload,
                self.config.timeout_seconds,
            ),
            self.config.max_retries,
        )
        return AIProviderResult(
            provider="openai",
            model=self.config.model,
            output=_openai_output(response),
            elapsed_seconds=round(time.perf_counter() - started, 3),
        )


def build_provider(config: AIProviderConfig | None = None, *, transport: Transport = _default_transport):
    cfg = config or AIProviderConfig.from_environment()
    if cfg.provider == "gemini":
        return GeminiProvider(cfg, transport=transport)
    if cfg.provider == "openai":
        return OpenAIProvider(cfg, transport=transport)
    raise AIProviderError(
        "Desteklenmeyen AI sağlayıcısı. Geçerli değerler: gemini, openai."
    )
