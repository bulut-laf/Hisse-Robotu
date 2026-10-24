# Sprint-37 — Veri Tazeliği Güvenlik Kilidi

## Amaç

Momentum, toplu tarama ve güncel teknik analiz sonuçlarının eski günlük kapanış verisiyle kullanılmasını önlemek.

## Eklenenler

- İstanbul saati ve BIST kapanış saati (18:10) esas alınarak beklenen son tamamlanmış işlem günü hesabı.
- Veri sağlayıcının kapanış barını yayınlaması için 20 dakikalık güvenlik süresi.
- Seans içinde önceki tamamlanmış işlem gününün normal kabul edilmesi.
- Seans kapanışı sonrasında bugünkü tamamlanmış bar yoksa veri tazeliği kilidi.
- Hafta sonlarında son cuma barının beklenen tarih kabul edilmesi.
- Momentum Keşif, BIST Toplu Tarama ve Güncel Teknik Analiz ekranlarında ayrı veri tazeliği kartı.
- Son fiyat veri tarihi, beklenen tarih, iş günü gecikmesi ve toplu taramadaki eski sembol sayısının gösterimi.
- Eski, boş veya gelecek tarihli veride aday sıralaması, teknik teyit, stop, hedef ve lot değerlerinin ekranda durdurulması.
- Sistem kontrolüne veri tazeliği güvenlik zinciri.

## Not

Resmî tatil günleri için politika katmanı kapalı tarih listesi kabul eder. İlk sürüm hafta sonlarını otomatik yönetir; resmî tatil takviminin otomatik güncellenmesi sonraki veri altyapısı geliştirmesinde ele alınacaktır.

## Yerel doğrulama

- Yeni veri tazeliği testleri: 5/5 başarılı.
- Momentum, toplu tarama, canlı analiz ve sistem kontrolü regresyon grubu: 58/58 başarılı.
- Değiştirilen Python dosyaları sözdizimi kontrolünden geçti.
- Tam test paketi ve çevrimdışı sistem kontrolü kullanıcı bilgisayarındaki kurulum sırasında çalıştırılır.
