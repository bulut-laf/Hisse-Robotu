# Hisse Robotu — Fon Araştırma Sprint 1

## Amaç
Fon araştırması için ISIN bazlı kanonik evren ve doğrulanabilir veri modeli oluşturmak. Mevcut hisse AL-SAT akışına dokunmaz.

## Kapsam
- ISIN ile tekilleştirme; aynı ISIN için çelişkili adları sessizce birleştirmeme.
- Fon türü, para birimleri, sağlayıcı, ücret alanları, risk göstergesi, doğrulama durumu ve birden fazla kaynak URL'si.
- JSON yükleme/kaydetme; eksik dosyada boş evren; bozuk JSON ve desteklenmeyen şemada açık hata.
- Bilinmeyen değerler `null`, doğrulama durumu `unverified`; performans/ücret verisi uydurulmaz.

## Bu sprintte yok
Performans hesaplama, maliyet normalizasyonu, korelasyon/örtüşme, portföy optimizasyonu ve yatırım önerisi.

## Hedef test
`python -m unittest backend.tests.test_fund_research_sprint1 -v`

Kurulumdan sonra hedef testler ve ardından tam regresyon çalıştırılmalıdır. Bu paket hazırlanırken kullanıcının yerel deposuna erişim olmadığı için tam proje regresyonu çalıştırılmadı.
