from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from .fundamental_report import FundamentalReport


class FundamentalReportArchiveError(ValueError):
    """Temel analiz rapor arşivi işlemi başarısız oldu."""


@dataclass(frozen=True)
class ArchivedFundamentalReport:
    report_id: str
    data_identity: str
    symbol: str
    period_key: str
    period_end: date
    created_at: datetime
    report: FundamentalReport


@dataclass(frozen=True)
class FundamentalReportArchiveSaveResult:
    inserted: int
    unchanged: int
    archived: ArchivedFundamentalReport


@dataclass(frozen=True)
class FundamentalReportComparison:
    symbol: str
    previous_period: str
    current_period: str
    total_score_change: int | None
    component_changes: tuple[tuple[str, int], ...]
    ratio_changes: tuple[tuple[str, str, str], ...]
    sector_ranking_change: tuple[str, str]
    sector_strength_change: tuple[str, str]
    source_change: tuple[str, str]
    freshness_change: tuple[str, str]


def _json_default(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"JSON'a çevrilemeyen değer: {type(value)!r}")


def _report_payload(report: FundamentalReport) -> dict[str, Any]:
    payload = asdict(report)
    payload["period_end"] = report.period_end.isoformat()
    payload["generated_at"] = report.generated_at.astimezone(
        timezone.utc
    ).isoformat()
    return payload


def _data_identity(report: FundamentalReport) -> str:
    payload = _report_payload(report)
    payload.pop("generated_at", None)
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=_json_default,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _report_from_payload(payload: dict[str, Any]) -> FundamentalReport:
    return FundamentalReport(
        symbol=str(payload["symbol"]),
        period_key=str(payload["period_key"]),
        period_end=date.fromisoformat(str(payload["period_end"])),
        currency=str(payload["currency"]),
        source=str(payload["source"]),
        freshness_status=str(payload["freshness_status"]),
        age_days=(
            int(payload["age_days"])
            if payload.get("age_days") is not None
            else None
        ),
        total_score=(
            int(payload["total_score"])
            if payload.get("total_score") is not None
            else None
        ),
        grade=str(payload["grade"]),
        component_scores=tuple(
            (str(name), int(score), int(maximum))
            for name, score, maximum
            in payload.get("component_scores", ())
        ),
        score_change=str(payload["score_change"]),
        ratio_rows=tuple(
            (str(metric), str(value))
            for metric, value in payload.get("ratio_rows", ())
        ),
        sector_ratio_rows=tuple(
            (
                str(metric),
                str(company),
                str(sector_median),
                str(position),
            )
            for metric, company, sector_median, position
            in payload.get("sector_ratio_rows", ())
        ),
        sector_ranking=str(payload["sector_ranking"]),
        sector_strength=str(payload["sector_strength"]),
        quality_flags=tuple(
            str(flag) for flag in payload.get("quality_flags", ())
        ),
        generated_at=datetime.fromisoformat(
            str(payload["generated_at"])
        ),
        disclaimer=str(payload.get("disclaimer", "")),
    )


class FundamentalReportJsonArchive:
    def __init__(
        self,
        path: Path | str = Path(
            "backend/data/fundamental_report_archive.json"
        ),
    ) -> None:
        self.path = Path(path)

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FundamentalReportArchiveError(
                "Temel rapor arşivi okunamadı."
            ) from exc
        if not isinstance(raw, list):
            raise FundamentalReportArchiveError(
                "Temel rapor arşiv biçimi geçersiz."
            )
        return raw

    def _write(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(
                records,
                ensure_ascii=False,
                indent=2,
                default=_json_default,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _to_archived(
        record: dict[str, Any],
    ) -> ArchivedFundamentalReport:
        try:
            report = _report_from_payload(record["report"])
            return ArchivedFundamentalReport(
                report_id=str(record["report_id"]),
                data_identity=str(record["data_identity"]),
                symbol=str(record["symbol"]).upper(),
                period_key=str(record["period_key"]),
                period_end=date.fromisoformat(
                    str(record["period_end"])
                ),
                created_at=datetime.fromisoformat(
                    str(record["created_at"])
                ),
                report=report,
            )
        except Exception as exc:
            raise FundamentalReportArchiveError(
                "Arşivde geçersiz temel rapor kaydı bulundu."
            ) from exc

    def save(
        self,
        report: FundamentalReport,
    ) -> FundamentalReportArchiveSaveResult:
        identity = _data_identity(report)
        records = self._read()

        for record in records:
            if (
                str(record.get("symbol", "")).upper()
                == report.symbol.upper()
                and str(record.get("data_identity", ""))
                == identity
            ):
                archived = self._to_archived(record)
                return FundamentalReportArchiveSaveResult(
                    inserted=0,
                    unchanged=1,
                    archived=archived,
                )

        created_at = datetime.now(timezone.utc)
        report_id = (
            f"{report.symbol.upper()}-{report.period_key}-"
            f"{created_at.strftime('%Y%m%dT%H%M%S%fZ')}"
        )
        record = {
            "report_id": report_id,
            "data_identity": identity,
            "symbol": report.symbol.upper(),
            "period_key": report.period_key,
            "period_end": report.period_end.isoformat(),
            "created_at": created_at.isoformat(),
            "report": _report_payload(report),
        }
        records.append(record)
        self._write(records)

        return FundamentalReportArchiveSaveResult(
            inserted=1,
            unchanged=0,
            archived=self._to_archived(record),
        )

    def list_symbol(
        self,
        symbol: str,
        *,
        maximum_age_days: int = 1095,
        today: date | None = None,
    ) -> tuple[ArchivedFundamentalReport, ...]:
        normalized = symbol.strip().upper()
        if not normalized:
            raise FundamentalReportArchiveError(
                "Şirket sembolü boş olamaz."
            )
        if maximum_age_days < 1:
            raise FundamentalReportArchiveError(
                "Azami rapor yaşı en az 1 gün olmalıdır."
            )

        reference = today or date.today()
        items = []
        for record in self._read():
            if str(record.get("symbol", "")).upper() != normalized:
                continue
            archived = self._to_archived(record)
            age_days = (reference - archived.period_end).days
            if age_days < 0 or age_days > maximum_age_days:
                continue
            items.append(archived)

        return tuple(
            sorted(
                items,
                key=lambda item: (
                    item.period_end,
                    item.created_at,
                ),
                reverse=True,
            )
        )


def compare_archived_reports(
    previous: ArchivedFundamentalReport,
    current: ArchivedFundamentalReport,
) -> FundamentalReportComparison:
    if previous.symbol != current.symbol:
        raise FundamentalReportArchiveError(
            "Yalnızca aynı şirkete ait raporlar karşılaştırılabilir."
        )
    if previous.period_end > current.period_end:
        raise FundamentalReportArchiveError(
            "Önceki rapor güncel rapordan daha yeni olamaz."
        )
    if previous.report.currency != current.report.currency:
        raise FundamentalReportArchiveError(
            "Farklı para birimindeki raporlar karşılaştırılamaz."
        )

    old_total = previous.report.total_score
    new_total = current.report.total_score
    total_change = (
        new_total - old_total
        if old_total is not None and new_total is not None
        else None
    )

    old_components = {
        name: score
        for name, score, _ in previous.report.component_scores
    }
    new_components = {
        name: score
        for name, score, _ in current.report.component_scores
    }
    common_components = sorted(
        set(old_components) & set(new_components)
    )
    component_changes = tuple(
        (
            name,
            new_components[name] - old_components[name],
        )
        for name in common_components
    )

    old_ratios = dict(previous.report.ratio_rows)
    new_ratios = dict(current.report.ratio_rows)
    common_ratios = sorted(set(old_ratios) & set(new_ratios))
    ratio_changes = tuple(
        (
            metric,
            old_ratios[metric],
            new_ratios[metric],
        )
        for metric in common_ratios
        if old_ratios[metric] != new_ratios[metric]
    )

    return FundamentalReportComparison(
        symbol=current.symbol,
        previous_period=previous.period_key,
        current_period=current.period_key,
        total_score_change=total_change,
        component_changes=component_changes,
        ratio_changes=ratio_changes,
        sector_ranking_change=(
            previous.report.sector_ranking,
            current.report.sector_ranking,
        ),
        sector_strength_change=(
            previous.report.sector_strength,
            current.report.sector_strength,
        ),
        source_change=(
            previous.report.source,
            current.report.source,
        ),
        freshness_change=(
            previous.report.freshness_status,
            current.report.freshness_status,
        ),
    )


def report_archive_rows(
    reports: Iterable[ArchivedFundamentalReport],
) -> list[dict[str, object]]:
    return [
        {
            "Rapor kimliği": item.report_id,
            "Şirket": item.symbol,
            "Dönem": item.period_key,
            "Dönem sonu": item.period_end,
            "Temel skor": item.report.total_score,
            "Kalite sınıfı": item.report.grade,
            "Kaynak": item.report.source,
            "Tazelik": item.report.freshness_status,
            "Oluşturulma": item.created_at,
        }
        for item in reports
    ]


def report_comparison_rows(
    comparison: FundamentalReportComparison,
) -> list[dict[str, object]]:
    rows = [
        {
            "Gösterge": "Toplam temel skor değişimi",
            "Önceki": comparison.previous_period,
            "Güncel": comparison.current_period,
            "Değişim": comparison.total_score_change,
        }
    ]
    rows.extend(
        {
            "Gösterge": name,
            "Önceki": "",
            "Güncel": "",
            "Değişim": change,
        }
        for name, change in comparison.component_changes
    )
    rows.extend(
        {
            "Gösterge": metric,
            "Önceki": previous,
            "Güncel": current,
            "Değişim": "Metinsel oran değişimi",
        }
        for metric, previous, current in comparison.ratio_changes
    )
    rows.extend(
        (
            {
                "Gösterge": "Sektör sıralaması",
                "Önceki": comparison.sector_ranking_change[0],
                "Güncel": comparison.sector_ranking_change[1],
                "Değişim": "",
            },
            {
                "Gösterge": "Sektör güç haritası",
                "Önceki": comparison.sector_strength_change[0],
                "Güncel": comparison.sector_strength_change[1],
                "Değişim": "",
            },
            {
                "Gösterge": "Veri kaynağı",
                "Önceki": comparison.source_change[0],
                "Güncel": comparison.source_change[1],
                "Değişim": "",
            },
            {
                "Gösterge": "Tazelik",
                "Önceki": comparison.freshness_change[0],
                "Güncel": comparison.freshness_change[1],
                "Değişim": "",
            },
        )
    )
    return rows
