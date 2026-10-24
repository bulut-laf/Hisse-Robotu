from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from backend.app.market_context.ai_live_evaluation import (
    evaluate_daily_package_with_ai,
)
from backend.app.market_context.store import MarketContextStore


Evaluator = Callable[[dict[str, Any]], dict[str, Any]]


class DailyAIReviewError(RuntimeError):
    """Günlük AI değerlendirme zinciri çalıştırılamadığında yükseltilir."""


class DailyAIReviewService:
    """Arşivlenmiş günlük piyasa raporlarını canlı AI değerlendirmesine bağlar.

    Bu servis yalnızca piyasa bağlamı değerlendirmesi üretir.
    Teknik skor, sinyal, AL/SAT kararı veya pozisyon önerisi üretmez.
    """

    def __init__(
        self,
        *,
        data_root: str | Path,
        evaluator: Evaluator | None = None,
    ):
        self.data_root = Path(data_root)
        self.store = MarketContextStore(self.data_root)
        self.evaluator = evaluator or evaluate_daily_package_with_ai
        self.evaluation_root = self.data_root / "market_context_ai_evaluations"

    def build_daily_package(self, document_date: str) -> dict[str, Any]:
        manifest = self.store.load_manifest(document_date)

        reports: list[dict[str, Any]] = []
        for ref in manifest.documents:
            if not ref.processed_path:
                continue

            processed_path = self.data_root / ref.processed_path
            if not processed_path.exists():
                continue

            try:
                payload = json.loads(processed_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            reports.append(
                {
                    "document_id": payload.get("document_id", ref.document_id),
                    "source": payload.get("source", ref.source),
                    "document_date": payload.get("document_date", ref.document_date),
                    "input_type": payload.get("input_type", ref.input_type),
                    "raw_text": payload.get("raw_text", ""),
                    "structured_context": {
                        "index_outlook": payload.get("index_outlook"),
                        "supports": list(payload.get("supports", [])),
                        "resistances": list(payload.get("resistances", [])),
                        "external_market_outlook": payload.get("external_market_outlook"),
                        "futures_outlook": payload.get("futures_outlook"),
                        "macro_risks": list(payload.get("macro_risks", [])),
                        "sector_impacts": list(payload.get("sector_impacts", [])),
                        "stock_news": list(payload.get("stock_news", [])),
                        "notes": list(payload.get("notes", [])),
                    },
                }
            )

        return {
            "date": document_date,
            "report_count": len(reports),
            "sources": sorted(
                {
                    str(item.get("source", "")).strip()
                    for item in reports
                    if str(item.get("source", "")).strip()
                }
            ),
            "reports": reports,
            "instruction_context": (
                "Aynı güne ait raporları birlikte değerlendir. "
                "Kaynaklar arası uyum ve çelişkileri belirt. "
                "Yalnızca verilen raporlara dayan; veri uydurma. "
                "Nihai yanıt Türkçe olsun."
            ),
        }

    def run_daily_review(self, document_date: str) -> dict[str, Any]:
        package = self.build_daily_package(document_date)

        if package["report_count"] <= 0:
            return {
                "ok": False,
                "status": "no_reports",
                "review_id": "",
                "record": {},
                "error": "Seçili tarih için AI değerlendirmesine uygun arşivlenmiş rapor yok.",
            }

        result = self.evaluator(package)

        if not isinstance(result, dict):
            return {
                "ok": False,
                "status": "provider_error",
                "review_id": "",
                "record": {},
                "error": "AI sağlayıcısı geçersiz yanıt döndürdü.",
            }

        if not result.get("ok"):
            return {
                "ok": False,
                "status": str(result.get("status", "provider_error")),
                "review_id": "",
                "record": {},
                "error": str(result.get("error", "AI değerlendirmesi tamamlanamadı.")),
            }

        output = result.get("output")
        if not isinstance(output, dict) or not output:
            return {
                "ok": False,
                "status": "rejected",
                "review_id": "",
                "record": {},
                "error": "AI değerlendirmesi boş çıktı üretti.",
            }

        review_id = uuid4().hex
        record = {
            "review_id": review_id,
            "date": document_date,
            "created_at": self._utc_now_iso(),
            "provider": str(result.get("provider", "")),
            "model": str(result.get("model", "")),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "report_count": package["report_count"],
            "sources": list(package["sources"]),
            "document_ids": [
                item["document_id"]
                for item in package["reports"]
                if item.get("document_id")
            ],
            "output": dict(output),
        }

        self._save_record(record)

        manifest = self.store.load_manifest(document_date)
        manifest.ai_review_status = "reviewed"
        manifest.ai_review_id = review_id
        manifest.updated_at = self._utc_now_iso()
        manifest.save(self._manifest_path(document_date))

        return {
            "ok": True,
            "status": "reviewed",
            "review_id": review_id,
            "record": record,
            "error": "",
        }

    def load_latest_review(self, document_date: str) -> dict[str, Any] | None:
        manifest = self.store.load_manifest(document_date)
        if not manifest.ai_review_id:
            return None

        path = self._record_path(document_date, manifest.ai_review_id)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict):
            return None

        return payload

    def _save_record(self, record: dict[str, Any]) -> Path:
        path = self._record_path(record["date"], record["review_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def _record_path(self, document_date: str, review_id: str) -> Path:
        return self.evaluation_root / document_date / f"{review_id}.json"

    def _manifest_path(self, document_date: str) -> Path:
        return (
            self.data_root
            / "market_context_archive"
            / document_date
            / "daily_manifest.json"
        )

    @staticmethod
    def _utc_now_iso() -> str:
        return (
            datetime.now(UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
