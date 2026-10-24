# Sprint-116 — Piyasa Rejimine Göre E2–E4 Performans Karşılaştırması

## Amaç
Gerçek erken yakalama sonuçlarını yükselen, yatay ve zayıf piyasa rejimlerinde ayrı ölçmek.

## Kapsam
- E2/E3/E4 aşamalarını rejim bazında karşılaştırır.
- 20 seans tamamlanmamış sonuçları başarı oranına katmaz.
- Başarılı / Sınırlı hareket / Başarısız ayrımını korur.
- Her rejim+aşama için örneklem, başarı oranı, ortalama 20G kapanış ve maksimum hareketi raporlar.
- Minimum örneklem altındaki gruplardan lider çıkarmaz.
- Bilinmeyen rejimi görünür tutar fakat güvenilir lider seçimine dahil etmez.
- Üretim eşiklerini otomatik değiştirmez.

## Güvenlik ilkesi
Bu sprint post-hoc doğrulama katmanıdır. Gelecek veriler yalnız performans ölçümünde kullanılır; aday üretiminde kullanılmaz.
