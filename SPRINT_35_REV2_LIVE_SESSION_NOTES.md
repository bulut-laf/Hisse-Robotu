# Sprint-35 Rev2 — Güncel Seans Karşılaştırma Hotfix'i

## Amaç

Tarihsel yeniden oynatma sonuçları yalnızca tamamlanmış günlük barlarla ölçülür. Gün içinde oluşan yeni en yüksek fiyat, tarihsel ölçüme karıştırılmadan ayrı bir kartta gösterilir.

## Eklenenler

- Tarihsel aday ayrıntısına **Güncel seans karşılaştırması** bölümü eklendi.
- Veri yalnızca kullanıcı **Güncel seans verisini getir** düğmesine bastığında alınır.
- Son erişilebilir seansın 5 dakikalık verisinden şu alanlar gösterilir:
  - seans tarihi ve son veri zamanı,
  - son fiyat,
  - gün içi en yüksek ve en düşük fiyat,
  - sinyal fiyatına göre son getiri,
  - canlı seans dâhil azami yükseliş,
  - canlı seans ters hareketi.
- Güncel seans tepesi, tamamlanmış barlara dayalı tarihsel tepeden yüksekse fark ayrıca bildirilir.
- Veri sağlayıcı bugünkü seansı henüz vermiyorsa son mevcut seans açıkça belirtilir.

## Güvenlik ilkesi

Güncel seans verisi tarihsel aday üretiminde, sınıflandırmada veya walk-forward performansında kullanılmaz. Böylece gelecek veri sızıntısı oluşmaz; canlı değerler yalnızca karşılaştırma amaçlıdır.

## Doğrulama

- Otomatik testler: **582/582 başarılı**
- Sistem kontrolleri: **18/18 başarılı**
