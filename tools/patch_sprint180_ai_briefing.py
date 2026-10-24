from __future__ import annotations

import argparse
from pathlib import Path


MARKER = "SPRINT-180: kapsamlı günlük piyasa brifingi"

NEW_FUNCTION = '''def build_live_evaluation_prompt(daily_package: dict[str, Any]) -> str:\n    """Tüm günlük raporları dengeli ve kaynak-duyarlı değerlendirme isteğine dönüştürür."""\n\n    contract = AIPromptContract().to_dict()\n    reports = daily_package.get("reports", [])\n    report_count = len(reports) if isinstance(reports, list) else 0\n    return (\n        "Aşağıdaki Hisse Robotu piyasa bağlamını kapsamlı bir günlük piyasa "\n        "brifingi olarak değerlendir.\\n\\n"\n        "KURALLAR:\\n"\n        f"- Rol: {contract['role']}\\n"\n        f"- Kapsam: {contract['scope']}\\n"\n        f"- Dil: {contract['language']}\\n"\n        f"- Kanıt: {contract['evidence_policy']}\\n"\n        f"- Belirsizlik: {contract['uncertainty_policy']}\\n"\n        f"- Çelişki: {contract['conflict_policy']}\\n"\n        f"- Risk ayrımı: {contract['risk_classification_policy']}\\n"\n        f"- Güvenlik: {contract['safety_policy']}\\n"\n        f"- SPRINT-180: kapsamlı günlük piyasa brifingi. Pakette {report_count} rapor var.\\n"\n        "- reports[] içindeki HER raporu tek tek oku; uzun bir raporun diğer kaynakları "\n        "gölgelemesine izin verme ve maddi bir başlığı sessizce atlama.\\n"\n        "- Sentezden önce her kaynak için endeks görünümü/destek-direnc, makro-jeopolitik, "\n        "sektör, hisse/KAP, bilanço-beklenti ve izlenecek olay başlıklarını zihinsel olarak tara.\\n"\n        "- summary alanını yalnız birkaç cümlelik özetle sınırlama; varsa genel piyasa, "\n        "endeks seviyeleri, makro-jeopolitik, sektör, hisse/KAP ve bilanço başlıklarını "\n        "kısa paragraflarla birlikte kapsa.\\n"\n        "- aligned_points alanında birden fazla kaynağın aynı yöndeki ortak noktalarını; "\n        "conflicting_points alanında kaynaklar arası gerçek çelişkileri belirt.\\n"\n        "- watch_items alanına kaynaklarda açıkça geçen önemli veri/olay/hisse başlıklarını "\n        "kaynak içeriğine sadık kalarak ekle.\\n"\n        "- Aracı kurum AL/TUT/SAT gibi tavsiye etiketlerini Hisse Robotu'nun kendi tavsiyesi "\n        "olarak yeniden üretme. Bu etiketlerin ayrıntısı deterministik kaynak panelinde gösterilir.\\n"\n        "- Girdinin dili Türkçe olmak zorunda değildir. Yabancı dildeki finansal metinleri "\n        "anlamını koruyarak değerlendir.\\n"\n        "- Orijinal kaynakta bulunmayan hedef fiyat, olay, veri veya gerekçe ekleme.\\n"\n        "- Yalnızca istenen yapılandırılmış alanları üret.\\n\\n"\n        "PIYASA_BAGLAMI_JSON:\\n"\n        + json.dumps(\n            daily_package,\n            ensure_ascii=False,\n            sort_keys=True,\n            default=str,\n        )\n    )\n'''


def _find_function_span(text: str) -> tuple[int, int]:
    start_token = "def build_live_evaluation_prompt(daily_package: dict[str, Any]) -> str:"
    end_token = "\n\ndef evaluate_daily_package_with_ai("
    start = text.find(start_token)
    if start < 0:
        raise RuntimeError("build_live_evaluation_prompt fonksiyonu bulunamadı.")
    end = text.find(end_token, start)
    if end < 0:
        raise RuntimeError("evaluate_daily_package_with_ai sınırı bulunamadı.")
    return start, end


def _validate_known_contract(block: str) -> None:
    required = (
        "AIPromptContract().to_dict()",
        "PIYASA_BAGLAMI_JSON",
        "json.dumps(",
        "contract['safety_policy']",
    )
    missing = [item for item in required if item not in block]
    if missing:
        raise RuntimeError(
            "AI prompt sözleşmesi beklenmeyen yapıda; eksik işaretler: " + ", ".join(missing)
        )


def patch(path: Path, *, check_only: bool) -> str:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return "already_patched"

    start, end = _find_function_span(text)
    current = text[start:end]
    _validate_known_contract(current)
    if check_only:
        return "compatible"

    updated = text[:start] + NEW_FUNCTION.rstrip() + text[end:]
    path.write_text(updated, encoding="utf-8", newline="\n")
    return "patched"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    status = patch(args.path, check_only=args.check)
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
