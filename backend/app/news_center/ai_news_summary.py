from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import time
from typing import Any, Callable, Iterable
from urllib import error, request


NEWS_SUMMARY_MAX_ITEMS = 120
NEWS_SUMMARY_MAX_BODY_CHARS = 600
NEWS_SUMMARY_MAX_DEVELOPMENTS = 10
NEWS_SUMMARY_DEFAULT_TIMEOUT_SECONDS = 45.0


class AINewsSummaryError(RuntimeError):
    """Halka açık haberlerin AI özeti güvenle üretilemediğinde oluşur."""


@dataclass(frozen=True, slots=True)
class NewsSummaryInput:
    source_id: str
    channel_name: str
    source_name: str
    published_at: datetime
    headline: str
    body: str
    event_type: str = ""
    market_scope: str = ""
    sectors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("source_id", "channel_name", "source_name", "headline"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"{field_name} boş olamaz.")
            object.__setattr__(self, field_name, value)
        if self.published_at.tzinfo is None or self.published_at.utcoffset() is None:
            raise ValueError("published_at saat dilimi içermelidir.")
        object.__setattr__(self, "body", " ".join(str(self.body or "").split()).strip())
        object.__setattr__(self, "event_type", str(self.event_type or "").strip())
        object.__setattr__(self, "market_scope", str(self.market_scope or "").strip())
        object.__setattr__(
            self,
            "sectors",
            tuple(str(item or "").strip() for item in self.sectors if str(item or "").strip()),
        )


@dataclass(frozen=True, slots=True)
class AINewsSummaryResult:
    provider: str
    model: str
    input_count: int
    output: dict[str, Any]
    elapsed_seconds: float
    generated_at: datetime


Transport = Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]]


NEWS_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "market_summary": {"type": "string"},
        "key_developments": {
            "type": "array",
            "maxItems": NEWS_SUMMARY_MAX_DEVELOPMENTS,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "importance": {
                        "type": "string",
                        "enum": ["YUKSEK", "ORTA", "DUSUK"],
                    },
                    "why_it_matters": {"type": "string"},
                    "source_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "title",
                    "summary",
                    "importance",
                    "why_it_matters",
                    "source_ids",
                ],
                "additionalProperties": False,
            },
        },
        "themes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "watch_items": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["market_summary", "key_developments", "themes", "watch_items"],
    "additionalProperties": False,
}


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
        raise AINewsSummaryError(
            f"AI sağlayıcı HTTP hatası: {exc.code}. {detail[:500]}"
        ) from exc
    except (error.URLError, TimeoutError) as exc:
        raise AINewsSummaryError(f"AI sağlayıcı bağlantı hatası: {exc}") from exc

    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AINewsSummaryError("AI sağlayıcı geçerli JSON yanıtı döndürmedi.") from exc
    if not isinstance(value, dict):
        raise AINewsSummaryError("AI sağlayıcı yanıtı nesne biçiminde değil.")
    return value


def _json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(str(text or "").strip())
    except json.JSONDecodeError as exc:
        raise AINewsSummaryError("AI modeli yapılandırılmış JSON çıktı üretmedi.") from exc
    if not isinstance(value, dict):
        raise AINewsSummaryError("AI modeli JSON nesnesi üretmedi.")
    return value


def _gemini_output(response: dict[str, Any]) -> dict[str, Any]:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AINewsSummaryError("Gemini yanıtında aday çıktı bulunamadı.")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ).strip()
    if not text:
        raise AINewsSummaryError("Gemini boş metin çıktısı döndürdü.")
    return _json_object(text)


def _openai_output(response: dict[str, Any]) -> dict[str, Any]:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return _json_object(direct)
    output = response.get("output")
    if not isinstance(output, list):
        raise AINewsSummaryError("OpenAI yanıtında output alanı bulunamadı.")
    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        for part in item.get("content", []):
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str):
                texts.append(text)
    combined = "".join(texts).strip()
    if not combined:
        raise AINewsSummaryError("OpenAI boş metin çıktısı döndürdü.")
    return _json_object(combined)


def _clean_string_list(value: Any, *, max_items: int = 20) -> list[str] | None:
    if not isinstance(value, list) or len(value) > max_items:
        return None
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        result.append(item.strip())
    return result


def validate_news_summary_output(
    output: dict[str, Any],
    *,
    allowed_source_ids: set[str],
) -> bool:
    if not isinstance(output, dict):
        return False
    if set(output) != {"market_summary", "key_developments", "themes", "watch_items"}:
        return False
    if not isinstance(output.get("market_summary"), str) or not output["market_summary"].strip():
        return False

    developments = output.get("key_developments")
    if not isinstance(developments, list) or len(developments) > NEWS_SUMMARY_MAX_DEVELOPMENTS:
        return False
    for item in developments:
        if not isinstance(item, dict):
            return False
        if set(item) != {"title", "summary", "importance", "why_it_matters", "source_ids"}:
            return False
        if any(
            not isinstance(item.get(field), str) or not item[field].strip()
            for field in ("title", "summary", "why_it_matters")
        ):
            return False
        if item.get("importance") not in {"YUKSEK", "ORTA", "DUSUK"}:
            return False
        source_ids = _clean_string_list(item.get("source_ids"), max_items=20)
        if source_ids is None or not source_ids:
            return False
        if any(source_id not in allowed_source_ids for source_id in source_ids):
            return False

    if _clean_string_list(output.get("themes"), max_items=12) is None:
        return False
    if _clean_string_list(output.get("watch_items"), max_items=12) is None:
        return False
    return True


def _normalized_items(items: Iterable[NewsSummaryInput]) -> tuple[NewsSummaryInput, ...]:
    materialized = tuple(items)
    if not materialized:
        raise ValueError("AI özeti için en az bir haber gerekir.")
    if len(materialized) > NEWS_SUMMARY_MAX_ITEMS:
        raise ValueError(f"AI özeti en fazla {NEWS_SUMMARY_MAX_ITEMS} haber kabul eder.")
    ids = [item.source_id for item in materialized]
    if len(ids) != len(set(ids)):
        raise ValueError("AI haber kaynak kimlikleri benzersiz olmalıdır.")
    return materialized


def build_news_summary_prompt(items: Iterable[NewsSummaryInput]) -> str:
    normalized = _normalized_items(items)
    rows = []
    for item in normalized:
        rows.append(
            {
                "id": item.source_id,
                "channel": item.channel_name,
                "source": item.source_name,
                "published_at": item.published_at.astimezone(timezone.utc).isoformat(),
                "headline": item.headline,
                "rss_summary": item.body[:NEWS_SUMMARY_MAX_BODY_CHARS],
                "event_type": item.event_type,
                "market_scope": item.market_scope,
                "sectors": list(item.sectors),
            }
        )

    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    return (
        "Sen Hisse Robotu Haber Merkezi için yalnız haber özetleme yapan bir asistansın.\n"
        "Aşağıdaki kayıtlar halka açık RSS başlık ve özetlerinden gelir. Yalnız verilen içeriği kullan; "
        "dış bilgi ekleme, doğrulanmamış ayrıntı üretme.\n"
        "Görev: aynı veya ilişkili gelişmeleri grupla; piyasa açısından bilgi değeri yüksek olan en fazla "
        f"{NEWS_SUMMARY_MAX_DEVELOPMENTS} gelişmeyi seç; önemli kısmı kısa Türkçe ile özetle; düşük bilgi değerli "
        "genel haberleri öne çıkarmak zorunda değilsin.\n"
        "Önem etiketi yalnız haber akışını sıralamak içindir. Teknik analiz skoru değildir. AL/SAT, hedef, stop, "
        "fiyat yönü, getiri beklentisi veya yatırım tavsiyesi üretme.\n"
        "BIST şirketi, sembolü veya sektörünü girişte açıkça desteklenmiyorsa uydurma. Belirsizliği açıkça belirt.\n"
        "Her key_developments kaydındaki source_ids yalnız aşağıdaki id değerlerinden oluşmalı ve kullanılan "
        "haberleri göstermelidir.\n"
        "market_summary tüm akışın kısa üst özetidir. themes tekrar eden ana temalardır. watch_items sonraki "
        "haberlerde izlenmesi gereken teyit/veri başlıklarıdır; işlem önerisi değildir.\n"
        "Yalnız tanımlı JSON şemasına uygun çıktı üret.\n"
        f"RSS_KAYITLARI={payload}"
    )


def _provider_settings() -> tuple[str, str, float, int]:
    provider = os.getenv("HISSE_ROBOTU_AI_PROVIDER", "gemini").strip().lower()
    if provider == "gemini":
        model = os.getenv("HISSE_ROBOTU_GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
    elif provider == "openai":
        model = os.getenv("HISSE_ROBOTU_OPENAI_MODEL", "gpt-5.6-luna").strip()
    else:
        raise AINewsSummaryError(
            "Desteklenmeyen AI sağlayıcısı. Geçerli değerler: gemini, openai."
        )
    try:
        timeout = float(os.getenv("HISSE_ROBOTU_AI_TIMEOUT", str(NEWS_SUMMARY_DEFAULT_TIMEOUT_SECONDS)))
        retries = int(os.getenv("HISSE_ROBOTU_AI_MAX_RETRIES", "1"))
    except ValueError as exc:
        raise AINewsSummaryError("AI zaman aşımı/yeniden deneme ayarı geçersiz.") from exc
    if not model:
        raise AINewsSummaryError("AI model adı tanımlı değil.")
    if timeout <= 0 or retries < 0 or retries > 3:
        raise AINewsSummaryError("AI zaman aşımı veya yeniden deneme sınırı geçersiz.")
    return provider, model, timeout, retries


def _call_with_retry(call: Callable[[], dict[str, Any]], retries: int) -> dict[str, Any]:
    last_error: AINewsSummaryError | None = None
    for attempt in range(retries + 1):
        try:
            return call()
        except AINewsSummaryError as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(min(0.5 * (attempt + 1), 1.5))
    raise AINewsSummaryError(str(last_error or "AI sağlayıcı çağrısı başarısız."))


def summarize_public_news(
    items: Iterable[NewsSummaryInput],
    *,
    transport: Transport = _default_transport,
) -> AINewsSummaryResult:
    normalized = _normalized_items(items)
    allowed_ids = {item.source_id for item in normalized}
    provider, model, timeout, retries = _provider_settings()
    prompt = build_news_summary_prompt(normalized)
    started = time.perf_counter()

    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise AINewsSummaryError("GEMINI_API_KEY tanımlı değil.")
        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{model}:generateContent"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "responseJsonSchema": NEWS_SUMMARY_SCHEMA,
            },
        }
        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        response = _call_with_retry(lambda: transport(url, headers, payload, timeout), retries)
        output = _gemini_output(response)
    else:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise AINewsSummaryError("OPENAI_API_KEY tanımlı değil.")
        payload = {
            "model": model,
            "input": prompt,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "public_news_summary",
                    "schema": NEWS_SUMMARY_SCHEMA,
                    "strict": True,
                }
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        response = _call_with_retry(
            lambda: transport("https://api.openai.com/v1/responses", headers, payload, timeout),
            retries,
        )
        output = _openai_output(response)

    if not validate_news_summary_output(output, allowed_source_ids=allowed_ids):
        raise AINewsSummaryError("AI haber özeti güvenlik/sözleşme doğrulamasını geçemedi.")

    return AINewsSummaryResult(
        provider=provider,
        model=model,
        input_count=len(normalized),
        output=output,
        elapsed_seconds=round(time.perf_counter() - started, 3),
        generated_at=datetime.now(timezone.utc),
    )
