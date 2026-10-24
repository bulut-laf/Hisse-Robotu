from __future__ import annotations

import json
from typing import Any

from backend.app.market_context.ai_output_validator import validate_ai_output
from backend.app.market_context.ai_prompt_contract import AIPromptContract
from backend.app.market_context.ai_provider import (
    AIProviderConfig,
    AIProviderError,
    build_provider,
)


def build_live_evaluation_prompt(daily_package: dict[str, Any]) -> str:
    contract = AIPromptContract().to_dict()
    return (
        "Aşağıdaki Hisse Robotu piyasa bağlamını değerlendir.\n\n"
        "KURALLAR:\n"
        f"- Rol: {contract['role']}\n"
        f"- Kapsam: {contract['scope']}\n"
        f"- Dil: {contract['language']}\n"
        f"- Kanıt: {contract['evidence_policy']}\n"
        f"- Belirsizlik: {contract['uncertainty_policy']}\n"
        f"- Çelişki: {contract['conflict_policy']}\n"
        f"- Güvenlik: {contract['safety_policy']}\n"
        "- Girdinin dili Türkçe olmak zorunda değildir. "
        "Yabancı dildeki finansal metinleri anlamını koruyarak değerlendir.\n"
        "- Orijinal kaynakta bulunmayan hedef fiyat, olay, veri veya gerekçe ekleme.\n"
        "- Yalnızca istenen yapılandırılmış alanları üret.\n\n"
        "PIYASA_BAGLAMI_JSON:\n"
        + json.dumps(
            daily_package,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
    )


def evaluate_daily_package_with_ai(
    daily_package: dict[str, Any],
    *,
    config: AIProviderConfig | None = None,
    provider=None,
) -> dict[str, Any]:
    if not isinstance(daily_package, dict) or not daily_package:
        return {
            "ok": False,
            "status": "invalid_input",
            "provider": "",
            "model": "",
            "output": {},
            "error": "Günlük AI paketi boş veya geçersiz.",
        }

    selected_provider = provider or build_provider(config)
    prompt = build_live_evaluation_prompt(daily_package)

    try:
        result = selected_provider.evaluate(prompt)
    except AIProviderError as exc:
        cfg = getattr(selected_provider, "config", None)
        return {
            "ok": False,
            "status": "provider_error",
            "provider": getattr(cfg, "provider", ""),
            "model": getattr(cfg, "model", ""),
            "output": {},
            "error": str(exc),
        }

    if not validate_ai_output(result.output):
        return {
            "ok": False,
            "status": "rejected",
            "provider": result.provider,
            "model": result.model,
            "output": {},
            "elapsed_seconds": result.elapsed_seconds,
            "error": "AI çıktısı güvenlik doğrulamasını geçemedi.",
        }

    return {
        "ok": True,
        "status": "accepted",
        "provider": result.provider,
        "model": result.model,
        "output": result.output,
        "elapsed_seconds": result.elapsed_seconds,
        "error": "",
    }
