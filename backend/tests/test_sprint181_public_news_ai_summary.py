from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from backend.app.news_center.ai_news_summary import (
    AINewsSummaryError,
    NEWS_SUMMARY_MAX_ITEMS,
    NewsSummaryInput,
    build_news_summary_prompt,
    summarize_public_news,
    validate_news_summary_output,
)


NOW = datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc)


def item(index: int = 1, **kwargs) -> NewsSummaryInput:
    data = dict(
        source_id=f"N{index:03d}",
        channel_name="TRT Haber Ekonomi",
        source_name="TRT Haber",
        published_at=NOW,
        headline=f"Ekonomi haberi {index}",
        body="RSS özet metni",
        event_type="DIGER",
        market_scope="OTHER",
        sectors=(),
    )
    data.update(kwargs)
    return NewsSummaryInput(**data)


def valid_output(source_id: str = "N001") -> dict:
    return {
        "market_summary": "Akışta istihdam ve piyasa düzenlemeleri öne çıkıyor.",
        "key_developments": [
            {
                "title": "İstihdam gelişmesi",
                "summary": "RSS kayıtları istihdam tarafında yeni bir gelişme bildiriyor.",
                "importance": "YUKSEK",
                "why_it_matters": "Türkiye makro görünümü açısından takip edilebilir.",
                "source_ids": [source_id],
            }
        ],
        "themes": ["İstihdam"],
        "watch_items": ["Yeni resmî veri teyidi"],
    }


def test_prompt_tum_rss_kayitlarini_kaynak_kimligiyle_tasir():
    prompt = build_news_summary_prompt([item(1), item(2, headline="İkinci haber")])
    assert "N001" in prompt and "N002" in prompt
    assert "Ekonomi haberi 1" in prompt and "İkinci haber" in prompt
    assert "Yalnız verilen içeriği kullan" in prompt


def test_prompt_yatirim_karari_uretmemeyi_acikca_soyler():
    prompt = build_news_summary_prompt([item()])
    assert "AL/SAT" in prompt
    assert "hedef" in prompt
    assert "fiyat yönü" in prompt
    assert "yatırım tavsiyesi" in prompt


def test_saat_dilimsiz_haber_ozet_girdisi_reddedilir():
    with pytest.raises(ValueError, match="saat dilimi"):
        item(published_at=datetime(2026, 8, 10, 9, 0))


def test_ozet_girdi_siniri_rss_ust_sinirini_kapsar():
    rows = [item(index) for index in range(1, NEWS_SUMMARY_MAX_ITEMS + 1)]
    prompt = build_news_summary_prompt(rows)
    assert f"N{NEWS_SUMMARY_MAX_ITEMS:03d}" in prompt
    with pytest.raises(ValueError, match="en fazla"):
        build_news_summary_prompt(rows + [item(NEWS_SUMMARY_MAX_ITEMS + 1)])


def test_gecerli_ai_ozeti_kaynak_kimlikleriyle_kabul_edilir():
    assert validate_news_summary_output(
        valid_output(),
        allowed_source_ids={"N001"},
    ) is True


def test_ai_ozeti_bilinmeyen_kaynak_kimligi_uyduramaz():
    assert validate_news_summary_output(
        valid_output("N999"),
        allowed_source_ids={"N001"},
    ) is False


def test_gemini_toplu_ozet_yapilandirilmis_json_semasi_kullanir(monkeypatch):
    monkeypatch.setenv("HISSE_ROBOTU_AI_PROVIDER", "gemini")
    monkeypatch.setenv("HISSE_ROBOTU_GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("HISSE_ROBOTU_AI_MAX_RETRIES", "0")
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps(valid_output(), ensure_ascii=False)}
                        ]
                    }
                }
            ]
        }

    result = summarize_public_news([item()], transport=transport)
    assert result.provider == "gemini"
    assert result.model == "gemini-test"
    assert result.input_count == 1
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    config = captured["payload"]["generationConfig"]
    assert config["responseMimeType"] == "application/json"
    assert config["responseJsonSchema"]["additionalProperties"] is False


def test_openai_toplu_ozet_yapilandirilmis_json_semasi_kullanir(monkeypatch):
    monkeypatch.setenv("HISSE_ROBOTU_AI_PROVIDER", "openai")
    monkeypatch.setenv("HISSE_ROBOTU_OPENAI_MODEL", "openai-test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("HISSE_ROBOTU_AI_MAX_RETRIES", "0")
    captured = {}

    def transport(url, headers, payload, timeout):
        captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return {"output_text": json.dumps(valid_output(), ensure_ascii=False)}

    result = summarize_public_news([item()], transport=transport)
    assert result.provider == "openai"
    assert result.model == "openai-test"
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["payload"]["text"]["format"]["strict"] is True
    assert captured["headers"]["Authorization"] == "Bearer test-key"


def test_ai_uydurma_kaynak_kimligi_doner_ise_ozet_reddedilir(monkeypatch):
    monkeypatch.setenv("HISSE_ROBOTU_AI_PROVIDER", "gemini")
    monkeypatch.setenv("HISSE_ROBOTU_GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("HISSE_ROBOTU_AI_MAX_RETRIES", "0")

    def transport(url, headers, payload, timeout):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps(valid_output("N999"), ensure_ascii=False)}
                        ]
                    }
                }
            ]
        }

    with pytest.raises(AINewsSummaryError, match="doğrulamasını geçemedi"):
        summarize_public_news([item()], transport=transport)
