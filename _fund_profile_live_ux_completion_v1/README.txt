HISSE ROBOTU — FUND PROFILE LIVE UX COMPLETION V1

Bu blok önceki FUND_PROFILE_AUTO_REFRESH_V1 üzerine uygulanır.

Eklenen görünür profil katmanları:
- Fon fiyat geçmişi grafiği
- Fon toplam değeri geçmişi grafiği
- Yatırımcı sayısı geçmişi grafiği
- Son iki KAP snapshot'ından portföy değişim özeti
- Yeni giriş / artırılan / azaltılan / tam çıkış / belirsiz sayaçları
- Detaylı son portföy değişim tablosu
- TEFAS ve KAP veri tazeliği paneli
- Mevcut seçili-fon otomatik refresh sözleşmesi korunur

Güvenlik:
- Manuel araçlar fallback olarak korunur
- AL/SAT mutation yok
- Canonical ranking mutation yok

Kurulum sözleşmesi:
1. git apply --check
2. tek Git patch
3. target tests
4. full regression
5. başarısızlıkta otomatik rollback
