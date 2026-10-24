HISSE ROBOTU — FUND PROFILE & AUTO REFRESH V1

Hedef
- Fon seçildiğinde fiyat, günlük değişim, fon toplam değeri, yatırımcı sayısı,
  dönemsel getiriler ve güncel KAP portföyünü tek profil ekranında göstermek.
- Uygulama açıkken TEFAS fon evrenini otomatik güncel tutmak.
- Seçili fonun TEFAS detay/geçmiş, KAP portföy ve KAP/MKK FDO verilerini
  bounded otomatik refresh ile yenilemek.

Otomatik yenileme
- Başarılı refresh aralığı: 6 saat
- Kaynak hatasında retry throttle: 1 saat
- Son iyi canonical veri korunur
- 2.000+ fon için detail crawl yapılmaz; yalnız seçili fon detaylanır

UI
- Fon seçici
- Fiyat
- Günlük getiri
- Fon toplam değeri
- Yatırımcı sayısı
- 1H / 1A / 3A / 6A / YTD / 1Y
- Güncel KAP portföyü

Güvenlik
- Manuel PDF/CSV yalnız fallback
- AL/SAT authority yok
- Canonical ranking mutation yok
