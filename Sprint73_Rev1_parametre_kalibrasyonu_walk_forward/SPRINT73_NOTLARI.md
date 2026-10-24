# Sprint-73 Rev1 — Parametre Kalibrasyonu ve Walk-Forward Doğrulama

Eklenenler:
- Zamansal olarak ayrılmış eğitim ve doğrulama pencereleri
- Yürüyen pencere / step yapısı
- 5/10/20 işlem günü ölçüm ufukları
- Kalite skoru, risk/getiri ve ATR eşik kalibrasyonu
- Günlük trend, haftalık trend, momentum, hacim ve uyumsuzluk şartları
- Minimum eğitim ve doğrulama örneği güvenlik kilitleri
- Eğitim ve doğrulama başarı oranı
- Ortalama getiri, MFE, MAE ve maksimum düşüş
- Eğitimde iyi olup doğrulamada zayıflayan parametrelerin reddi
- Parametre kararlılık skoru
- Kararlı bölge / İzlenebilir / Aşırı uyum riski sınıfları
- CSV dışa aktarımı
- Dashboard'da Walk-forward doğrulama sekmesi

Güvenlik:
- Kayıtlar sinyal tarihine göre sıralanır.
- Eğitim dönemi yalnızca geçmiş kayıtları kullanır.
- Doğrulama dönemi eğitim döneminden sonraki kayıtları kullanır.
- Tek bir en iyi kombinasyon yerine tekrar eden kararlı bölgeler raporlanır.
- Sonuçlar gelecek performansı garanti etmez.
