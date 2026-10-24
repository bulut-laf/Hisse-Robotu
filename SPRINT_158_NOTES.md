# Sprint-158 — Bugünün Önemli Gelişmeleri

## Amaç

Haber Merkezi arşivindeki aynı gün olaylarını tek karar ekranında deterministik
olarak özetlemek.

## Kurallar

- Yeni bir 0–100 skor üretilmez.
- Ana sıralama mevcut olay önem skorudur.
- Eşit önem skorunda yalnız sıralama desteği olarak:
  - birincil/resmî kaynak varlığı,
  - çoklu kaynak teyidi,
  - açık Gölge Portföy teması,
  - olay zamanı kullanılır.
- Kullanıcı değerlendirme gününü ve asgari önem eşiğini seçebilir.
- Birincil kaynak, kaynak sayısı, sektör/hisse bağlantıları ve portföy teması
  aynı tabloda gösterilir.
- Fiyat yönü, AL/SAT kararı, teknik skor veya AI yorumu üretilmez.

## Değiştirilmeyenler

- SQLite şeması
- 0–100 önem formülü
- olay gruplama
- etki motoru
- Portföy Etki Radarı
- Sektör Etki Haritası
- Sprint-155 Aktif Trader
- Sprint-157 Seans Öncesi Görsel Girdi
