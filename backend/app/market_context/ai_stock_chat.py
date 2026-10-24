from __future__ import annotations

import json
import os
import re
import time
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from typing import Any, Callable
from urllib import error, request

from backend.app.market_context.ai_provider import (
    AIProviderConfig,
    AIProviderError,
)


CHAT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
        "uncertainties": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["answer", "evidence", "uncertainties"],
    "additionalProperties": False,
}

_MAX_CONTEXTS = 5
_MAX_HISTORY_MESSAGES = 12
_MAX_MESSAGE_CHARS = 6000

Transport = Callable[
    [str, dict[str, str], dict[str, Any], float],
    dict[str, Any],
]

_DIRECT_TRADE_PATTERNS = (
    re.compile(r"\b(bu\s+hisseyi\s+)?al(?:ın|in|malısın|malisin|ınız|iniz)?\b", re.I),
    re.compile(r"\b(bu\s+hisseyi\s+)?sat(?:ın|in|malısın|malisin|ınız|iniz)?\b", re.I),
    re.compile(r"\b(alım|alim|satım|satim)\s+fırsatı\b", re.I),
    re.compile(r"\bhedef\s+fiyat(?:ım|im)?\b", re.I),
    re.compile(r"\bstop(?:-loss)?\s+(?:koy|belirle|seviyesi)\b", re.I),
)


def _default_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url=url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise AIProviderError(
            f"AI sağlayıcı HTTP hatası: {exc.code}. {detail[:500]}"
        ) from exc
    except (error.URLError, TimeoutError) as exc:
        raise AIProviderError(
            f"AI sağlayıcı bağlantı hatası: {exc}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIProviderError(
            "AI sağlayıcı geçerli JSON yanıtı döndürmedi."
        ) from exc

    if not isinstance(data, dict):
        raise AIProviderError(
            "AI sağlayıcı yanıtı nesne biçiminde değil."
        )
    return data


def _safe_value(value: Any, depth: int = 0) -> Any:
    if depth > 8:
        return str(value)

    if value is None or isinstance(value, (str, int, bool)):
        return value

    if isinstance(value, float):
        if value != value:
            return None
        return value

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if is_dataclass(value):
        return {
            field.name: _safe_value(
                getattr(value, field.name),
                depth + 1,
            )
            for field in fields(value)
        }

    if isinstance(value, dict):
        return {
            str(key): _safe_value(item, depth + 1)
            for key, item in list(value.items())[:100]
        }

    if isinstance(value, (list, tuple, set)):
        return [
            _safe_value(item, depth + 1)
            for item in list(value)[:100]
        ]

    if hasattr(value, "item"):
        try:
            return _safe_value(value.item(), depth + 1)
        except Exception:
            pass

    return str(value)


def build_stock_analysis_context(result: Any) -> dict[str, Any]:
    """
    AI'a yalnızca hesaplanmış analiz sonucunu verir.
    Ham OHLCV / çoklu zaman dilimi paketini özellikle dışarıda bırakır.
    """
    technical = getattr(result, "teknik_teyit", None)
    plan = getattr(result, "islem_plani", None)
    freshness = getattr(result, "veri_tazeligi", None)
    analysis_request = getattr(result, "istek", None)

    symbol = str(
        getattr(technical, "sembol", "")
        or getattr(analysis_request, "sembol", "")
    ).strip()

    analysis_id = str(
        getattr(technical, "analiz_kimligi", "")
        or ""
    ).strip()

    return {
        "symbol": symbol,
        "analysis_id": analysis_id,
        "technical_confirmation": _safe_value(technical),
        "trade_plan": _safe_value(plan),
        "data_freshness": _safe_value(freshness),
        "request": _safe_value(analysis_request),
    }


def store_stock_ai_context(st: Any, result: Any) -> None:
    context = build_stock_analysis_context(result)
    symbol = context["symbol"]
    if not symbol:
        return

    contexts = dict(
        st.session_state.get(
            "_hisse_robotu_ai_stock_contexts",
            {},
        )
    )
    contexts[symbol] = context

    if len(contexts) > _MAX_CONTEXTS:
        keys = list(contexts)
        for key in keys[:-_MAX_CONTEXTS]:
            contexts.pop(key, None)

    st.session_state["_hisse_robotu_ai_stock_contexts"] = contexts
    st.session_state["_hisse_robotu_ai_current_symbol"] = symbol


def _history_for_prompt(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for item in messages[-_MAX_HISTORY_MESSAGES:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        cleaned.append(
            {
                "role": role,
                "content": content[:_MAX_MESSAGE_CHARS],
            }
        )
    return cleaned


def build_stock_chat_prompt(
    *,
    question: str,
    current_symbol: str,
    contexts: dict[str, dict[str, Any]],
    messages: list[dict[str, str]],
) -> str:
    current = contexts.get(current_symbol, {})
    available = {
        symbol: context
        for symbol, context in list(contexts.items())[-_MAX_CONTEXTS:]
    }

    payload = {
        "current_symbol": current_symbol,
        "current_analysis": current,
        "available_session_analyses": available,
        "conversation": _history_for_prompt(messages),
        "user_question": question.strip(),
    }

    return (
        "Sen Hisse Robotu içindeki AI Analiz Asistanısın.\n"
        "Görevin yalnızca Hisse Robotu'nun hesapladığı teknik sonuçları "
        "açıklamak, ilişkilendirmek ve karşılaştırmaktır.\n\n"
        "ZORUNLU KURALLAR:\n"
        "- Varsayılan yanıt dili Türkçedir.\n"
        "- Yalnızca aşağıdaki ANALIZ_BAGLAMI_JSON içindeki verilere dayan.\n"
        "- Bağlamda olmayan fiyat, gösterge, haber, bilanço, olay veya seviye uydurma.\n"
        "- Teknik skorları, yönleri, risk/ödül oranlarını veya robot kararlarını değiştirme.\n"
        "- Robotun mevcut durumunu açıklayabilirsin; yeni AL/SAT sinyali üretme.\n"
        "- Yeni hedef fiyat, stop seviyesi, lot veya pozisyon büyüklüğü önerme.\n"
        "- Kullanıcı birden fazla hisseyi karşılaştırırsa yalnızca "
        "available_session_analyses içinde bulunan hisseleri karşılaştır.\n"
        "- İstenen hisse bağlamda yoksa, önce o hissede Güncel Teknik Analiz "
        "çalıştırılması gerektiğini açıkça söyle.\n"
        "- Veri ile yorum ayrımını koru. Çıkarım yapıyorsan bunu 'yorum' olarak belirt.\n"
        "- Belirsiz veya eksik veri varsa kesin ifade kullanma.\n"
        "- Kısa ama gerekçeli, doğal bir sohbet cevabı ver.\n\n"
        "Yalnızca şu JSON yapısını üret:\n"
        '{"answer":"...", "evidence":["..."], "uncertainties":["..."]}\n\n'
        "ANALIZ_BAGLAMI_JSON:\n"
        + json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
    )


def _validate_output(output: dict[str, Any]) -> tuple[bool, str]:
    if set(output) != {"answer", "evidence", "uncertainties"}:
        return False, "AI sohbet çıktısı beklenen alanları taşımıyor."

    answer = output.get("answer")
    evidence = output.get("evidence")
    uncertainties = output.get("uncertainties")

    if not isinstance(answer, str) or not answer.strip():
        return False, "AI sohbet cevabı boş."
    if not isinstance(evidence, list) or not all(
        isinstance(x, str) for x in evidence
    ):
        return False, "AI kanıt listesi geçersiz."
    if not isinstance(uncertainties, list) or not all(
        isinstance(x, str) for x in uncertainties
    ):
        return False, "AI belirsizlik listesi geçersiz."

    for pattern in _DIRECT_TRADE_PATTERNS:
        if pattern.search(answer):
            return (
                False,
                "AI cevabı doğrudan işlem yönlendirmesi içerdiği için reddedildi.",
            )

    return True, ""


def _json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIProviderError(
            "AI modeli yapılandırılmış JSON sohbet çıktısı üretmedi."
        ) from exc
    if not isinstance(value, dict):
        raise AIProviderError(
            "AI modeli sohbet için JSON nesnesi döndürmedi."
        )
    return value


def _gemini_response(response: dict[str, Any]) -> dict[str, Any]:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AIProviderError(
            "Gemini sohbet yanıtında aday çıktı bulunamadı."
        )
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict)
        and isinstance(part.get("text"), str)
    ).strip()
    if not text:
        raise AIProviderError("Gemini boş sohbet cevabı döndürdü.")
    return _json_object(text)


def _openai_response(response: dict[str, Any]) -> dict[str, Any]:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return _json_object(direct.strip())

    output = response.get("output")
    if not isinstance(output, list):
        raise AIProviderError(
            "OpenAI sohbet yanıtında output alanı bulunamadı."
        )

    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        for part in item.get("content", []):
            if (
                isinstance(part, dict)
                and isinstance(part.get("text"), str)
            ):
                texts.append(part["text"])

    text = "".join(texts).strip()
    if not text:
        raise AIProviderError("OpenAI boş sohbet cevabı döndürdü.")
    return _json_object(text)


def _call_with_retry(
    call: Callable[[], dict[str, Any]],
    retries: int,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return call()
        except AIProviderError as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(min(0.5 * (attempt + 1), 1.5))
    raise AIProviderError(
        str(last_error or "AI sohbet çağrısı başarısız.")
    )


def ask_stock_ai(
    *,
    question: str,
    current_symbol: str,
    contexts: dict[str, dict[str, Any]],
    messages: list[dict[str, str]],
    config: AIProviderConfig | None = None,
    transport: Transport = _default_transport,
) -> dict[str, Any]:
    question = question.strip()
    if not question:
        return {
            "ok": False,
            "answer": "",
            "evidence": [],
            "uncertainties": [],
            "provider": "",
            "model": "",
            "elapsed_seconds": 0.0,
            "error": "Soru boş olamaz.",
        }

    cfg = config or AIProviderConfig.from_environment()
    prompt = build_stock_chat_prompt(
        question=question,
        current_symbol=current_symbol,
        contexts=contexts,
        messages=messages,
    )

    started = time.perf_counter()

    try:
        if cfg.provider == "gemini":
            key = os.getenv("GEMINI_API_KEY", "").strip()
            if not key:
                raise AIProviderError("GEMINI_API_KEY tanımlı değil.")
            if not cfg.model:
                raise AIProviderError("Gemini model adı tanımlı değil.")

            url = (
                "https://generativelanguage.googleapis.com/"
                f"v1beta/models/{cfg.model}:generateContent"
            )
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                    "responseJsonSchema": CHAT_OUTPUT_SCHEMA,
                },
            }
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": key,
            }
            response = _call_with_retry(
                lambda: transport(
                    url,
                    headers,
                    payload,
                    cfg.timeout_seconds,
                ),
                cfg.max_retries,
            )
            output = _gemini_response(response)

        elif cfg.provider == "openai":
            key = os.getenv("OPENAI_API_KEY", "").strip()
            if not key:
                raise AIProviderError("OPENAI_API_KEY tanımlı değil.")
            if not cfg.model:
                raise AIProviderError("OpenAI model adı tanımlı değil.")

            payload = {
                "model": cfg.model,
                "input": prompt,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "stock_analysis_chat",
                        "schema": CHAT_OUTPUT_SCHEMA,
                        "strict": True,
                    }
                },
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            }
            response = _call_with_retry(
                lambda: transport(
                    "https://api.openai.com/v1/responses",
                    headers,
                    payload,
                    cfg.timeout_seconds,
                ),
                cfg.max_retries,
            )
            output = _openai_response(response)

        else:
            raise AIProviderError(
                "Desteklenmeyen AI sağlayıcısı. "
                "Geçerli değerler: gemini, openai."
            )

    except AIProviderError as exc:
        return {
            "ok": False,
            "answer": "",
            "evidence": [],
            "uncertainties": [],
            "provider": cfg.provider,
            "model": cfg.model,
            "elapsed_seconds": round(
                time.perf_counter() - started,
                3,
            ),
            "error": str(exc),
        }

    valid, error_message = _validate_output(output)
    if not valid:
        return {
            "ok": False,
            "answer": "",
            "evidence": [],
            "uncertainties": [],
            "provider": cfg.provider,
            "model": cfg.model,
            "elapsed_seconds": round(
                time.perf_counter() - started,
                3,
            ),
            "error": error_message,
        }

    return {
        "ok": True,
        "answer": output["answer"].strip(),
        "evidence": output["evidence"],
        "uncertainties": output["uncertainties"],
        "provider": cfg.provider,
        "model": cfg.model,
        "elapsed_seconds": round(
            time.perf_counter() - started,
            3,
        ),
        "error": "",
    }


def render_stock_ai_chat(st: Any) -> None:
    contexts = st.session_state.get(
        "_hisse_robotu_ai_stock_contexts",
        {},
    )
    current_symbol = st.session_state.get(
        "_hisse_robotu_ai_current_symbol",
        "",
    )

    if not contexts or not current_symbol:
        return

    st.divider()
    st.subheader("AI Analiz Asistanı")

    cfg = AIProviderConfig.from_environment()
    available_symbols = ", ".join(
        symbol.removesuffix(".IS")
        for symbol in contexts
    )
    st.caption(
        f"Bağlam: {available_symbols} · "
        f"Sağlayıcı: {cfg.provider} · Model: {cfg.model}"
    )
    st.info(
        "Asistan mevcut Hisse Robotu analizlerini açıklar ve karşılaştırır. "
        "Teknik skorları veya robot kararlarını değiştirmez; yeni işlem "
        "sinyali, hedef fiyat ya da stop seviyesi üretmez."
    )

    history_key = "_hisse_robotu_ai_stock_chat_messages"
    messages = list(st.session_state.get(history_key, []))

    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.caption(
            f"Aktif analiz: {current_symbol.removesuffix('.IS')}"
        )
    with top_right:
        if st.button(
            "Sohbeti temizle",
            key="stock_ai_chat_clear",
            width="stretch",
        ):
            st.session_state[history_key] = []
            st.rerun()

    for message in messages:
        role = message.get("role")
        content = str(message.get("content", ""))
        if role not in {"user", "assistant"}:
            continue
        with st.chat_message(role):
            st.markdown(content)

    question = st.chat_input(
        f"{current_symbol.removesuffix('.IS')} analizi hakkında sorun...",
        key="stock_ai_chat_input",
    )
    if not question:
        return

    messages.append(
        {
            "role": "user",
            "content": question[:_MAX_MESSAGE_CHARS],
        }
    )
    st.session_state[history_key] = messages

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("AI analiz bağlamını değerlendiriyor..."):
            result = ask_stock_ai(
                question=question,
                current_symbol=current_symbol,
                contexts=contexts,
                messages=messages[:-1],
                config=cfg,
            )

        if not result["ok"]:
            answer = (
                "AI değerlendirmesi tamamlanamadı: "
                + result["error"]
            )
            st.error(answer)
        else:
            answer = result["answer"]
            st.markdown(answer)

            if result["evidence"]:
                with st.expander("Dayanak alınan robot verileri"):
                    for item in result["evidence"]:
                        st.write(f"• {item}")

            if result["uncertainties"]:
                with st.expander("Belirsizlikler / eksik bağlam"):
                    for item in result["uncertainties"]:
                        st.write(f"• {item}")

            st.caption(
                f"{result['provider']} · {result['model']} · "
                f"{result['elapsed_seconds']:.2f} sn"
            )

    messages.append(
        {
            "role": "assistant",
            "content": answer[:_MAX_MESSAGE_CHARS],
        }
    )
    st.session_state[history_key] = messages[-20:]
