from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


DEFAULT_OPERATION_HEALTH_PATH = Path("backend/data/prebreakout_operation_health.json")


class HealthLevel(str, Enum):
    OK = "OK"
    UYARI = "UYARI"
    HATA = "HATA"


@dataclass(frozen=True)
class OperationalHealthCheck:
    code: str
    label: str
    level: HealthLevel
    message: str


@dataclass(frozen=True)
class OperationalHealthReport:
    run_date: str
    ready: bool
    overall_level: HealthLevel
    checks: tuple[OperationalHealthCheck, ...]
    error_count: int
    warning_count: int
    ok_count: int


def _check(code: str, label: str, level: HealthLevel, message: str) -> OperationalHealthCheck:
    return OperationalHealthCheck(code=code, label=label, level=level, message=message)


def _safe_len(value: Any) -> int:
    try:
        return len(value)
    except TypeError:
        return 0


def _invalid_or_missing_json(path: str | Path) -> str | None:
    target = Path(path)
    if not target.exists():
        return "Dosya bulunamadı."
    try:
        json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return f"JSON okunamadı: {error}"
    return None


def operasyon_sagligini_degerlendir(
    daily_result: Any,
    *,
    expected_run_date: date | None = None,
    daily_report_path: str | Path | None = None,
) -> OperationalHealthReport:
    """Sprint-100 günlük izleme zincirinin operasyonel bütünlüğünü denetler."""
    expected = (expected_run_date or date.today()).isoformat()
    actual_run_date = str(getattr(daily_result, "run_date", ""))
    total_signal_count = int(getattr(daily_result, "total_signal_count", 0) or 0)
    lifecycle_records = tuple(getattr(daily_result, "lifecycle_records", ()) or ())
    performance_records = tuple(getattr(daily_result, "performance_records", ()) or ())
    paper_trades = tuple(getattr(daily_result, "paper_trades", ()) or ())
    missing_symbols = tuple(getattr(daily_result, "missing_observation_symbols", ()) or ())
    portfolio_summary = getattr(daily_result, "portfolio_summary", None)

    checks: list[OperationalHealthCheck] = []

    if actual_run_date == expected:
        checks.append(_check("run_date", "Günlük çalışma tarihi", HealthLevel.OK, f"Günlük akış {expected} için tamamlandı."))
    else:
        checks.append(_check("run_date", "Günlük çalışma tarihi", HealthLevel.HATA, f"Beklenen {expected}; bulunan {actual_run_date or 'boş'}."))

    if missing_symbols:
        checks.append(_check(
            "market_data",
            "Fiyat verisi kapsamı",
            HealthLevel.HATA,
            f"Fiyat gözlemi eksik {len(missing_symbols)} sembol: {', '.join(sorted(str(x) for x in missing_symbols))}",
        ))
    else:
        checks.append(_check("market_data", "Fiyat verisi kapsamı", HealthLevel.OK, "Canlı izleme kayıtlarında eksik fiyat gözlemi yok."))

    count_sets = (
        ("lifecycle", "Yaşam döngüsü kayıtları", len(lifecycle_records)),
        ("performance", "Performans kayıtları", len(performance_records)),
        ("paper", "Deneme portföyü kayıtları", len(paper_trades)),
    )
    for code, label, count in count_sets:
        if count == total_signal_count:
            checks.append(_check(code, label, HealthLevel.OK, f"{count}/{total_signal_count} kayıt tutarlı."))
        else:
            checks.append(_check(code, label, HealthLevel.HATA, f"{count}/{total_signal_count} kayıt; zincir sayımı uyuşmuyor."))

    unmeasurable_count = sum(
        1 for item in performance_records
        if int(getattr(item, "available_session_count", 0) or 0) == 0
    )
    if unmeasurable_count:
        checks.append(_check(
            "measurability",
            "Performans ölçülebilirliği",
            HealthLevel.UYARI,
            f"{unmeasurable_count} sinyal için henüz ölçülebilir işlem günü yok.",
        ))
    else:
        checks.append(_check("measurability", "Performans ölçülebilirliği", HealthLevel.OK, "Tüm kayıtların en az bir işlem günü gözlemi var veya kayıt yok."))

    portfolio_count = int(getattr(portfolio_summary, "total_trade_count", 0) or 0)
    if portfolio_count == len(paper_trades):
        checks.append(_check("portfolio_summary", "Portföy özeti", HealthLevel.OK, f"Portföy özeti {portfolio_count} işlemi kapsıyor."))
    else:
        checks.append(_check("portfolio_summary", "Portföy özeti", HealthLevel.HATA, f"Özet {portfolio_count}, işlem listesi {len(paper_trades)} kayıt içeriyor."))

    if daily_report_path is not None:
        json_error = _invalid_or_missing_json(daily_report_path)
        if json_error is None:
            try:
                payload = json.loads(Path(daily_report_path).read_text(encoding="utf-8"))
                report_date = str(payload.get("run_date", "")) if isinstance(payload, Mapping) else ""
            except (OSError, UnicodeError, json.JSONDecodeError):
                report_date = ""
            if report_date == actual_run_date:
                checks.append(_check("daily_report", "Günlük özet dosyası", HealthLevel.OK, "Günlük özet JSON geçerli ve çalışma tarihiyle uyumlu."))
            else:
                checks.append(_check("daily_report", "Günlük özet dosyası", HealthLevel.HATA, f"Rapor tarihi {report_date or 'boş'}; çalışma tarihi {actual_run_date or 'boş'}."))
        else:
            checks.append(_check("daily_report", "Günlük özet dosyası", HealthLevel.HATA, json_error))

    error_count = sum(item.level is HealthLevel.HATA for item in checks)
    warning_count = sum(item.level is HealthLevel.UYARI for item in checks)
    ok_count = sum(item.level is HealthLevel.OK for item in checks)
    overall = HealthLevel.HATA if error_count else (HealthLevel.UYARI if warning_count else HealthLevel.OK)
    return OperationalHealthReport(
        run_date=actual_run_date,
        ready=error_count == 0,
        overall_level=overall,
        checks=tuple(checks),
        error_count=error_count,
        warning_count=warning_count,
        ok_count=ok_count,
    )


def operasyon_saglik_raporunu_kaydet(
    report: OperationalHealthReport,
    path: str | Path = DEFAULT_OPERATION_HEALTH_PATH,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    payload["overall_level"] = report.overall_level.value
    payload["checks"] = [
        {**asdict(item), "level": item.level.value}
        for item in report.checks
    ]
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def operasyon_sagligini_tabloya_cevir(report: OperationalHealthReport) -> list[dict[str, str]]:
    return [
        {
            "Kontrol": item.label,
            "Durum": item.level.value,
            "Açıklama": item.message,
        }
        for item in report.checks
    ]
