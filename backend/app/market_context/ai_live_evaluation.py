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
    """Tüm günlük raporları dengeli ve kaynak-duyarlı değerlendirme isteğine dönüştürür."""

    contract = AIPromptContract().to_dict()
    reports = daily_package.get("reports", [])
    report_count = len(reports) if isinstance(reports, list) else 0
    return (
        "Aşağıdaki Hisse Robotu piyasa bağlamını kapsamlı bir günlük piyasa "
        "brifingi olarak değerlendir.\n\n"
        "KURALLAR:\n"
        f"- Rol: {contract['role']}\n"
        f"- Kapsam: {contract['scope']}\n"
        f"- Dil: {contract['language']}\n"
        f"- Kanıt: {contract['evidence_policy']}\n"
        f"- Belirsizlik: {contract['uncertainty_policy']}\n"
        f"- Çelişki: {contract['conflict_policy']}\n"
        f"- Risk ayrımı: {contract['risk_classification_policy']}\n"
        f"- Güvenlik: {contract['safety_policy']}\n"
        f"- SPRINT-180: kapsamlı günlük piyasa brifingi. Pakette {report_count} rapor var.\n"
        "- reports[] içindeki HER raporu tek tek oku; uzun bir raporun diğer kaynakları "
        "gölgelemesine izin verme ve maddi bir başlığı sessizce atlama.\n"
        "- Sentezden önce her kaynak için endeks görünümü/destek-direnc, makro-jeopolitik, "
        "sektör, hisse/KAP, bilanço-beklenti ve izlenecek olay başlıklarını zihinsel olarak tara.\n"
        "- summary alanını yalnız birkaç cümlelik özetle sınırlama; varsa genel piyasa, "
        "endeks seviyeleri, makro-jeopolitik, sektör, hisse/KAP ve bilanço başlıklarını "
        "kısa paragraflarla birlikte kapsa.\n"
        "- aligned_points alanında birden fazla kaynağın aynı yöndeki ortak noktalarını; "
        "conflicting_points alanında kaynaklar arası gerçek çelişkileri belirt.\n"
        "- watch_items alanına kaynaklarda açıkça geçen önemli veri/olay/hisse başlıklarını "
        "kaynak içeriğine sadık kalarak ekle.\n"
        "- Aracı kurum AL/TUT/SAT gibi tavsiye etiketlerini Hisse Robotu'nun kendi tavsiyesi "
        "olarak yeniden üretme. Bu etiketlerin ayrıntısı deterministik kaynak panelinde gösterilir.\n"
        "- Girdinin dili Türkçe olmak zorunda değildir. Yabancı dildeki finansal metinleri "
        "anlamını koruyarak değerlendir.\n"
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
