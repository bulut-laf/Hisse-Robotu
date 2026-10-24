# Sprint-117 — Kontrollü Model Kalibrasyonu ve Eşik Optimizasyonu

## Amaç
Sprint-114–116 gerçek kullanım doğrulama çıktılarından türetilen eşik adaylarını, aşırı uyum riskini azaltan güvenlik kapılarıyla değerlendirmek.

## Güvenlik ilkeleri
- Üretim eşikleri otomatik değiştirilmez.
- Küçük örneklemde yüksek başarı oranı kabul edilmez.
- Örneklem korunumu kontrol edilir.
- En az iki yeterli piyasa rejimi aranır.
- Yanlış pozitif oranındaki kötüleşme engellenir.
- En zayıf piyasa rejiminde aşırı performans kaybı engellenir.
- Hiçbir aday güvenlik kapılarını geçmezse mevcut eşikler korunur.

## Çıktı
Kontrollü kalibrasyon raporu; uygun aday varsa yalnızca öneri üretir. Otomatik uygulama kapalıdır.
