# Sprint-179 Rev2 — Seans Öncesi Bağlam Dosya Yükleyici Sıfırlama

## Amaç
Sprint-179 Rev1 sonrasında gerçek kullanımda görülen TXT/PDF `file_uploader` görsel durumunu güvenli biçimde sıfırlamak.

## Düzeltme
- Başarılı `İçeriği İşle ve Kaydet` işleminden sonra TXT/PDF yükleyicileri yeni widget nesliyle yeniden oluşturulur.
- Özellikle PDF dosya adı/ekli dosya görünümü ikinci içerikte kalmaz.
- Kullanıcının `PDF → Metin → PDF` seçimi yaparak alanı elle boşaltmasına gerek kalmaz.
- Kaynak, manuel metin ve görsel alanlarının Sprint-179 Rev1 temizliği korunur.
- Tarih korunur; aynı gün çoklu rapor girişi hızlandırılır.
- Başarısız/duplicate işlemlerde otomatik reset tetiklenmez.
- Mevcut Seans Öncesi Bağlam işleme/arşiv/AI motorları değiştirilmez.

## Teknik yaklaşım
Eski `market_context_pdf_file` / `market_context_txt_file` sözleşmesi proxy katmanında korunurken gerçek Streamlit widget anahtarı nesil numarasıyla değiştirilir. Başarılı kayıt sonrası nesil artırıldığı için Streamlit yeni ve boş bir uploader üretir.

## Kararlı taban
Başlangıç: Sprint-179 Rev1 — 2911 passed / 0 failed (kullanıcı doğrulaması).

## Doğrulama
Bu paket 3 yeni sözleşme testi ekler. Kullanıcı bilgisayarındaki tam regresyon geçmeden Rev2 kararlı ilan edilmez. Beklenen tam regresyon: 2914 passed / 0 failed.
