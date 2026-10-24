# Sprint-160 — KAP Akışı ve Hisse Bazlı Resmî Bildirim Görünümü

## Amaç

Haber Merkezi arşivine manuel olarak girilmiş ve güvenilir kaynak sözlüğü
üzerinden KAP olarak doğrulanmış bildirimleri ayrı bir operasyon ekranında
izlemek.

## İlk sürüm kapsamı

- Yeni `KAP Akışı` sekmesi.
- Yalnız kaynak adı açıkça `KAP` olan veya kaynak referansı gerçek
  `kap.org.tr` alan adına çözümlenen kayıtlar akışa alınır.
- “KAP benzeri” kaynak adları veya URL yolunda KAP metni geçen başka alan
  adları KAP kabul edilmez.
- Dönem filtreleri: son 24 saat, 3 gün, 7 gün, tüm arşiv.
- Mevcut 0–100 olay önem skoruna göre asgari önem filtresi.
- Hisse filtresi.
- Açık Gölge Portföy ile **yalnız doğrudan hisse sembolü kesişimi**.
- “Yalnız Gölge Portföy” filtresi.
- Özet metrikleri: KAP bildirimi, benzersiz hisse, önem ≥80, portföy teması,
  sembolsüz bildirim.
- Ana akış sırası yayın zamanına göre en yeniden eskiye.
- Hisse sembolü olmayan kayıt için sistem sembol uydurmaz.

## Bilinçli olarak yapılmayanlar

- Otomatik KAP internet/API entegrasyonu yok.
- KAP sayfası scraping yok.
- Haber/KAP içeriğinden otomatik sembol uydurma yok.
- Fiyat yönü, olumlu/olumsuz etki, AL/SAT veya teknik skor yok.
- AI yorumu yok.

## Korunan zincir

Sprint-159 Ekonomik Takvim, Sprint-158 Bugünün Önemli Gelişmeleri,
Sprint-156 Sektör Etki Haritası, Sprint-154 Portföy Etki Radarı ve mevcut
Haber Merkezi arşiv/sınıflandırma/etki motorları değişmeden korunur.
