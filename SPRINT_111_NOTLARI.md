# Sprint-111 — Karar Açıklaması ve Kullanıcı Aksiyon Özeti

## Amaç
Sprint-110 operasyon güven skoru ile ÇALIŞTIR / BEKLE / İNCELE kararını, teknik ayrıntıya boğmadan günlük kullanıcının anlayacağı kısa neden ve aksiyon özetine dönüştürmek.

## Eklenenler
- Operasyon karar açıklama modeli.
- NORMAL / DIKKAT / DUR kullanıcı önceliği.
- Kök nedeni sade Türkçe ifadeye dönüştürme.
- En fazla 3 neden ve 3 aksiyon ile gürültü kontrolü.
- BEKLE kararında yeniden denemeyi zorunlu olarak kapatma.
- İNCELE kararında kurtarma rehberindeki güvenli yeniden deneme bilgisini koruma.
- Atomik JSON kayıt ve tablo çıktısı.

## Güvenlik
Bu sprint otomatik düzeltme, otomatik yeniden deneme veya gerçek emir üretmez. Yalnızca mevcut teşhis/kurtarma/güven sonuçlarını sadeleştirir.

## Başlangıç tabanı
Sprint-110 tamamlandı: 1401 passed.
