# Sprint-129 — Erken Radar + Olgunlaşma/Kâr Koruma Karar Katmanı

## Amaç
Sprint-127/128 ölçümlerini üretimde kullanılabilir ayrı bir karar katmanına dönüştürmek.

## Yeni çıktı
- Erken Radar: Yok / İzle / Yüksek Öncelik
- Erken Fırsat Puanı: 0-100
- Hareket Fazı
- Olgunlaşma: Normal / Olgunlaşıyor / Kâr Koruma
- Yeni giriş mesajı
- Mevcut pozisyon mesajı
- Gerekçeler

## Kritik mimari kural
Bu puan, mevcut Hisse Robotu teknik/momentum skorunun yerine geçmez.
Ana sıralama motorunun puanlarını değiştirmez.
Erken fırsat ve hareket yaşı ikinci bir karar ekseni olarak çalışır.

## İlk üretim varsayımları
- 11-20 ve 21-30 sıra bantları erken fırsat açısından avantajlı kabul edilir.
- E0/E1/E2 erken aşama bonusu alır.
- Yukarı sıra ivmesi, skor ivmesi ve momentum ivmesi erken fırsat puanını artırır.
- Gerçekleşmiş hareket ve hareket yaşı arttıkça erken fırsat puanı azalır.
- İlk 5 + yüksek hareket yaşı / yüksek gerçekleşmiş getiri = Kâr Koruma değerlendirmesi.

Bu eşikler Sprint-128 tarihsel toplu sonuçlarıyla ileride kalibre edilmek üzere başlangıç varsayımlarıdır.
