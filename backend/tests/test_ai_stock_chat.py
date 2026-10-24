from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from backend.app.market_context.ai_provider import AIProviderConfig
from backend.app.market_context.ai_stock_chat import (
    ask_stock_ai,
    build_stock_analysis_context,
    build_stock_chat_prompt,
    _validate_output,
)


def test_stock_context_excludes_raw_multitimeframe_package():
    result = SimpleNamespace(
        paket={"raw": "MUST_NOT_BE_INCLUDED"},
        teknik_teyit=SimpleNamespace(
            sembol="TKFEN.IS",
            analiz_kimligi="abc123",
            teyit_skoru=58,
            teyit_durumu="Teknik Teyit Bekleniyor",
        ),
        islem_plani=SimpleNamespace(
            karar="İşlem Yok",
            plan_tipi="Koşullu Alım Planı",
            atr_yuzde=4.27,
        ),
        veri_tazeligi=SimpleNamespace(
            son_veri_tarihi="2026-08-03",
            is_gunu_gecikmesi=0,
        ),
        istek=SimpleNamespace(sembol="TKFEN.IS"),
    )

    context = build_stock_analysis_context(result)

    assert context["symbol"] == "TKFEN.IS"
    assert context["analysis_id"] == "abc123"
    assert "paket" not in context
    assert "MUST_NOT_BE_INCLUDED" not in json.dumps(context)


def test_prompt_contains_multiturn_and_comparison_context():
    contexts = {
        "TKFEN.IS": {"symbol": "TKFEN.IS", "score": 58},
        "PASEU.IS": {"symbol": "PASEU.IS", "score": 52},
    }
    prompt = build_stock_chat_prompt(
        question="PASEU ile karşılaştır.",
        current_symbol="TKFEN.IS",
        contexts=contexts,
        messages=[
            {"role": "user", "content": "TKFEN neden bekliyor?"},
            {"role": "assistant", "content": "Hacim teyidi eksik."},
        ],
    )

    assert "PASEU ile karşılaştır." in prompt
    assert "TKFEN.IS" in prompt
    assert "PASEU.IS" in prompt
    assert "Hacim teyidi eksik." in prompt
    assert "yeni AL/SAT sinyali üretme" in prompt


def test_chat_output_rejects_direct_trade_instruction():
    ok, error = _validate_output(
        {
            "answer": "Bu hisseyi al.",
            "evidence": [],
            "uncertainties": [],
        }
    )
    assert ok is False
    assert "işlem yönlendirmesi" in error


def test_gemini_chat_uses_existing_environment_contract(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(
            url=url,
            headers=headers,
            payload=payload,
            timeout=timeout,
        )
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    {
                                        "answer": (
                                            "Robot verisine göre teknik "
                                            "teyit henüz tamamlanmamış."
                                        ),
                                        "evidence": ["Skor 58/100."],
                                        "uncertainties": [
                                            "Hacim teyidi yok."
                                        ],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        ]
                    }
                }
            ]
        }

    result = ask_stock_ai(
        question="Neden teyit bekleniyor?",
        current_symbol="TKFEN.IS",
        contexts={
            "TKFEN.IS": {
                "symbol": "TKFEN.IS",
                "technical_confirmation": {"teyit_skoru": 58},
            }
        },
        messages=[],
        config=AIProviderConfig(
            provider="gemini",
            model="gemini-3.5-flash-lite",
            max_retries=0,
        ),
        transport=transport,
    )

    assert result["ok"] is True
    assert result["provider"] == "gemini"
    assert "teknik teyit" in result["answer"]
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert (
        captured["payload"]["generationConfig"]["responseMimeType"]
        == "application/json"
    )
    schema = captured["payload"]["generationConfig"]["responseJsonSchema"]
    assert set(schema["required"]) == {
        "answer",
        "evidence",
        "uncertainties",
    }


def test_dashboard_connects_stock_ai_chat():
    dashboard = (
        Path(__file__).resolve().parents[1]
        / "dashboard.py"
    ).read_text(encoding="utf-8")

    assert "store_stock_ai_context(st, sonuc)" in dashboard
    assert "render_stock_ai_chat(st)" in dashboard
    assert "ai_stock_chat import" in dashboard
