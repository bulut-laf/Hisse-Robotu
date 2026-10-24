from __future__ import annotations

from dataclasses import dataclass
from enum import Enum



class EvidenceLevel(str, Enum):
    YETERSIZ = "Yetersiz"
    GELISIYOR = "Gelişiyor"
    YETERLI = "Yeterli"


class V2Decision(str, Enum):
    GOZLEME_DEVAM = "Gözleme devam"
    MEVCUT_ESIKLERI_KORU = "Mevcut eşikleri koru"
    KALIBRASYON_ADAYINI_INCELE = "Kalibrasyon adayını incele"


@dataclass(frozen=True)
class RealUseV2ClosureReport:
    technical_ready: bool
    evidence_level: EvidenceLevel
    decision: V2Decision
    measured_candidate_count: int
    success_rate_pct: float | None
    false_positive_rate_pct: float | None
    early_trigger_rate_pct: float | None
    average_trigger_session: float | None
    missed_opportunity_count: int
    too_strict_filter_count: int
    reliable_regime_group_count: int
    best_reliable_regime: str | None
    best_reliable_stage: str | None
    calibration_candidate: str | None
    automatic_apply_allowed: bool
    warnings: tuple[str, ...]
    executive_summary: str


def _attr(obj: object, name: str, default=None):
    return getattr(obj, name, default)


def _missed_count(report: object) -> int:
    value = _attr(report, "missed_opportunity_count", None)
    if value is not None:
        return int(value)
    opportunities = _attr(report, "opportunities", ())
    return len(tuple(opportunities))


def _too_strict_count(report: object) -> int:
    rows = tuple(_attr(report, "reason_rows", ()))
    return sum(bool(_attr(row, "too_strict", False)) for row in rows)


def gercek_kullanim_v2_kapanisini_degerlendir(
    candidate_quality: object,
    missed_opportunities: object,
    regime_performance: object,
    calibration: object,
) -> RealUseV2ClosureReport:
    """Sprint-114–117 bulgularını tek V2 kapanış raporunda birleştirir.

    Kapanış raporu üretim eşiklerini değiştirmez. Teknik kapanış ile model kanıt
    seviyesini ayırır; yetersiz örneklemde güçlü performans iddiası üretmez.
    """
    measured = int(candidate_quality.measured_count)
    reliable_groups = int(regime_performance.sufficient_group_count)
    sample_sufficient = bool(candidate_quality.sufficient_sample)

    warnings: list[str] = []
    if not sample_sufficient:
        warnings.append("E2-E4 ölçülen aday örneklemi henüz yetersiz")
    if reliable_groups < 2:
        warnings.append("Piyasa rejimi kırılımında güvenilir grup sayısı yetersiz")

    missed_count = _missed_count(missed_opportunities)
    too_strict_count = _too_strict_count(missed_opportunities)
    if too_strict_count:
        warnings.append(f"{too_strict_count} filtre kaçırılan fırsat açısından fazla katı görünüyor")

    calibration_candidate = calibration.recommended_scenario_name
    if calibration.automatic_apply_allowed:
        warnings.append("Kalibrasyon raporu otomatik uygulamaya izin veriyor; V2 kapanışı bunu güvenlik nedeniyle engeller")

    if sample_sufficient and reliable_groups >= 2:
        evidence = EvidenceLevel.YETERLI
    elif measured > 0 or reliable_groups > 0:
        evidence = EvidenceLevel.GELISIYOR
    else:
        evidence = EvidenceLevel.YETERSIZ

    if evidence is not EvidenceLevel.YETERLI:
        decision = V2Decision.GOZLEME_DEVAM
    elif calibration_candidate:
        decision = V2Decision.KALIBRASYON_ADAYINI_INCELE
    else:
        decision = V2Decision.MEVCUT_ESIKLERI_KORU

    best_regime = _attr(regime_performance.best_reliable_regime, "value", None)
    best_stage = regime_performance.best_reliable_stage

    technical_ready = True
    auto_apply = False

    if evidence is EvidenceLevel.YETERSIZ:
        summary = "Gerçek Kullanım V2 teknik olarak kapatılabilir; model performansı için veri henüz yetersiz, gözleme devam edilmeli."
    elif evidence is EvidenceLevel.GELISIYOR:
        summary = "Gerçek Kullanım V2 teknik olarak kapatılabilir; kanıt birikiyor ancak kalıcı eşik kararı için gözleme devam edilmeli."
    elif decision is V2Decision.KALIBRASYON_ADAYINI_INCELE:
        summary = f"Gerçek Kullanım V2 doğrulaması yeterli örnekleme ulaştı; {calibration_candidate} yalnız kontrollü inceleme adayıdır, otomatik uygulanmaz."
    else:
        summary = "Gerçek Kullanım V2 doğrulaması yeterli örnekleme ulaştı; mevcut eşiklerin korunması destekleniyor."

    return RealUseV2ClosureReport(
        technical_ready=technical_ready,
        evidence_level=evidence,
        decision=decision,
        measured_candidate_count=measured,
        success_rate_pct=candidate_quality.success_rate_pct,
        false_positive_rate_pct=candidate_quality.false_positive_rate_pct,
        early_trigger_rate_pct=candidate_quality.early_trigger_rate_pct,
        average_trigger_session=candidate_quality.average_trigger_session,
        missed_opportunity_count=missed_count,
        too_strict_filter_count=too_strict_count,
        reliable_regime_group_count=reliable_groups,
        best_reliable_regime=best_regime,
        best_reliable_stage=best_stage,
        calibration_candidate=calibration_candidate,
        automatic_apply_allowed=auto_apply,
        warnings=tuple(warnings),
        executive_summary=summary,
    )


def v2_kapanis_raporunu_metne_cevir(report: RealUseV2ClosureReport) -> str:
    def fmt(value: float | None) -> str:
        return "Ölçülemiyor" if value is None else f"{value:.2f}"

    warning_text = "Yok" if not report.warnings else " | ".join(report.warnings)
    calibration = report.calibration_candidate or "Yok"
    leader = (
        f"{report.best_reliable_regime} / {report.best_reliable_stage}"
        if report.best_reliable_regime and report.best_reliable_stage
        else "Yok"
    )
    return "\n".join(
        [
            "GERÇEK KULLANIM V2 - FINAL PERFORMANS RAPORU",
            f"Teknik hazır: {'EVET' if report.technical_ready else 'HAYIR'}",
            f"Kanıt seviyesi: {report.evidence_level.value}",
            f"Karar: {report.decision.value}",
            f"Ölçülen E2-E4 aday: {report.measured_candidate_count}",
            f"Başarı oranı (%): {fmt(report.success_rate_pct)}",
            f"Yanlış pozitif (%): {fmt(report.false_positive_rate_pct)}",
            f"Erken tetiklenme (%): {fmt(report.early_trigger_rate_pct)}",
            f"Ortalama tetiklenme seansı: {fmt(report.average_trigger_session)}",
            f"Kaçırılan güçlü fırsat: {report.missed_opportunity_count}",
            f"Fazla katı görünen filtre: {report.too_strict_filter_count}",
            f"Güvenilir rejim/aşama grubu: {report.reliable_regime_group_count}",
            f"Temkinli rejim/aşama lideri: {leader}",
            f"Kalibrasyon adayı: {calibration}",
            "Otomatik eşik uygulama: HAYIR",
            f"Uyarılar: {warning_text}",
            f"Yönetici özeti: {report.executive_summary}",
        ]
    )
