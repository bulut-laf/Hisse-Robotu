from __future__ import annotations

from typing import Any

from backend.app.market_context.ai_output_validator import (
    validate_ai_output,
)


def create_evaluation_record(
    *,
    date: str,
    package_id: str,
    output: dict[str, Any],
) -> dict[str, Any]:
    """
    AI değerlendirme çıktısını arşivlenebilir kayıt biçimine dönüştürür.

    Bu kayıt teknik işlem kararı üretmez.
    signal veya technical_score gibi işlem motoruna ait alanlar eklenmez.
    """
    return {
        "date": date,
        "input_package_id": package_id,
        "report_count": 1,
        "reports": [dict(output)],
    }


def process_ai_evaluation_response(
    response: dict[str, Any],
) -> dict[str, Any]:
    """
    AI değerlendirme servis akışı.

    Gerçek AI çağrısı yapmaz.
    Çıktıyı doğrulayıp kabul/red sonucu üretir.
    """
    valid = validate_ai_output(response)

    return {
        "valid": valid,
        "status": "accepted" if valid else "rejected",
        "output": response if valid else {},
    }