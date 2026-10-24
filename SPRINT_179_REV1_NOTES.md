# Sprint-179 Rev1 — Seans Öncesi Bağlam Görsel Aktarım UX Düzeltmesi

## Amaç
JPG/JPEG/PNG görselinden kullanıcı tarafından onaylanan metnin tekrar kopyala/yapıştır gerektirmeden mevcut `Bülten / haber metni` alanına aktarılması ve başarılı kayıt sonrasında ekranın ikinci içerik için temizlenmesi.

## Rev1 düzeltmesi
İlk Sprint-179 kurucusu mevcut `market_context_dashboard.py` içinde tek bir başarı mesajını birebir aradığı için kullanıcıdaki daha yeni Seans Öncesi Bağlam sürümünde güvenlik kontrolü gereksiz yere durdu. Rev1 bu kırılgan metin bağımlılığını kaldırır.

Başarılı kayıt artık mesajın cümlesine göre değil, `market_context_process` kayıt düğmesinin tıklanması ve ardından başarı durumunun oluşmasına göre algılanır. Hata veya duplicate uyarısında form temizlenmez.

## Kullanıcı akışı
1. JPG/JPEG/PNG yükle.
2. Görselden metni çıkar.
3. Metni kontrol et ve gerekiyorsa düzelt.
4. Kullanıcı onayını ver.
5. Onaylı metin otomatik olarak `Metin Yapıştır` / `Bülten / haber metni` alanına aktarılır.
6. Kaynak ve tarihi kontrol et.
7. `İçeriği İşle ve Kaydet`.
8. Başarılı kayıttan sonra kaynak, metin, TXT/PDF ve görsel/OCR durumları temizlenir; tarih korunur.

## Güvenlik sınırları
- Kullanıcı onayı olmadan görsel metni bağlam kaydına aktarılmaz.
- Görsel arşivleme/SHA-256 ve Gemini retry davranışı korunur.
- `market_context_dashboard.py` değiştirilmez.
- Haber Merkezi V1, teknik skor, Gölge Portföy ve trader motoru değiştirilmez.
- Başarısız/duplicate kayıtta giriş ekranı temizlenmez.

## Doğrulama hedefi
Sprint-179 yeni test sayısı değişmez: 8. Mevcut kararlı 2903 tabanında beklenen tam regresyon: 2911 passed / 0 failed.
