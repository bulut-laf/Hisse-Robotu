from backend.app.analysis.daily_buy_decision_calibration import CalibrationSlice
from backend.app.analysis.daily_buy_decision_threshold_recommendation import (
    build_threshold_recommendations,
    threshold_recommendation_rows,
)


def _slice(segment, *, hit, avg, status, sample=10, dimension="Teknik skor", horizon="1S"):
    return CalibrationSlice(
        dimension=dimension,
        segment=segment,
        horizon=horizon,
        sample_size=sample,
        positive_count=round(sample * hit / 100),
        hit_rate=hit,
        average_return=avg,
        status=status,
    )


def test_small_samples_never_create_threshold_change_recommendation():
    rec = build_threshold_recommendations((
        _slice("70-79", hit=100.0, avg=3.0, status="YETERSİZ VERİ", sample=9),
    ))[0]
    assert rec.recommendation == "YETERSİZ VERİ"
    assert rec.preferred_segment is None
    assert rec.review_segment is None


def test_supportive_only_recommends_keep_not_change():
    rec = build_threshold_recommendations((
        _slice("80+", hit=70.0, avg=2.0, status="DESTEKLEYİCİ"),
        _slice("70-79", hit=55.0, avg=0.5, status="İZLE"),
    ))[0]
    assert rec.recommendation == "MEVCUT EŞİĞİ KORU"
    assert rec.preferred_segment == "80+"
    assert rec.review_segment is None


def test_supportive_and_weak_segments_create_manual_review_candidate():
    rec = build_threshold_recommendations((
        _slice("80+", hit=72.0, avg=2.5, status="DESTEKLEYİCİ"),
        _slice("<70", hit=35.0, avg=-1.2, status="GÖZDEN GEÇİR"),
    ))[0]
    assert rec.recommendation == "EŞİK İNCELEME ADAYI"
    assert rec.preferred_segment == "80+"
    assert rec.review_segment == "<70"
    assert "otomatik eşik değişikliği yapılmaz" in rec.evidence


def test_weak_only_requests_manual_review():
    rec = build_threshold_recommendations((
        _slice("<1.5", hit=40.0, avg=-0.8, status="GÖZDEN GEÇİR", dimension="Risk/Getiri"),
    ))[0]
    assert rec.recommendation == "MANUEL GÖZDEN GEÇİR"
    assert rec.review_segment == "<1.5"


def test_rows_are_ui_ready():
    recs = build_threshold_recommendations((
        _slice("80+", hit=70.0, avg=2.0, status="DESTEKLEYİCİ"),
    ))
    rows = threshold_recommendation_rows(recs)
    assert rows[0]["Boyut"] == "Teknik skor"
    assert rows[0]["Öneri"] == "MEVCUT EŞİĞİ KORU"
    assert "Kanıt" in rows[0]
