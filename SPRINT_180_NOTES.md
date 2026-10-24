# Sprint-180 — Haber Merkezi V1.1 Halka Açık Haber Akışı Temeli

## Neden Sprint-180?
Kaynak pakette `backend/tests/test_sprint179_market_context_image_ux.py` bulunduğu için Sprint-179 kimliği mevcut çalışma ağacında zaten kullanılmış görünmektedir. Geçmişi ezmemek için yeni Haber Merkezi geliştirmesi Sprint-180 olarak açılmıştır.

## Amaç
Haber Merkezi'nin yalnız resmî kaynak URL'leriyle sınırlı kalmaması; açık RSS yayınlayan doğrulanmış haber kaynaklarından yeni/son dakika haberlerini kullanıcı tarafından başlatılan tek yenileme akışıyla alabilmesi.

## İlk canlı kaynaklar
- Anadolu Ajansı — Ekonomi RSS
- TRT Haber — Ekonomi RSS
- TRT Haber — Son Dakika RSS

## Güvenlik sınırları
- Yalnız sabit ve beyaz listedeki HTTPS RSS URL'leri.
- Redirect sonrası alan adı yeniden doğrulanır.
- Yanıt boyutu en fazla 2 MB.
- Timeout 1–30 saniye.
- Haber detay sayfaları topluca scrape edilmez; RSS başlık/özet/link bilgisi kullanılır.
- Ağ erişimi kullanıcı onayı ve butonla başlar.
- Arşive yazma ayrı açık kullanıcı eylemidir.
- Teknik skor, fiyat yönü, AL/SAT veya AI işlem kararı üretilmez.
- Hisse sembolü metinden otomatik tahmin edilmez.

## Akış
RSS → güvenli fetch → XML parse → kaynak doğrulama → deterministik olay/kapsam sınıflaması → duplicate önizleme → açık onay → mevcut Haber Merkezi arşivi → Son Dakika / diğer mevcut ekranlar.

## V1.1 sonraki adım
Canlı doğrulama sonrasında kontrollü periyodik yenileme ve public-feed operasyon audit'i ayrı sprintte değerlendirilecektir. Görüntü tabanlı PDF fallback de bağımsız takip işidir.
