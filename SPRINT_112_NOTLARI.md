# Sprint-112 — Günlük Operasyon Kapanış Özeti ve Açık Riskler

## Amaç
Gün sonunda operasyon kararını, güven skorunu, açık alarm/riskleri ve bekleyen aksiyonları tek kapanış özetinde toplamak.

## Güvenlik ilkeleri
- Kritik açık risk varsa gün kapanmış sayılmaz.
- DUR/BEKLE önceliği kapanışı engeller.
- Günlük karar günlüğü kaydı olmadan kapanış tamamlanmaz.
- Uyarı seviyesindeki açık riskler izlenir; tek başına kritik blokaj oluşturmaz.
- Eski fakat çözülmemiş alarmlar açık risk olarak taşınır.
- Bu sprint alarm çözmez, veri değiştirmez ve otomatik yeniden deneme başlatmaz.

## Yeni dosyalar
- backend/app/prebreakout/prebreakout_operation_closure.py
- backend/tests/test_prebreakout_operation_closure.py
