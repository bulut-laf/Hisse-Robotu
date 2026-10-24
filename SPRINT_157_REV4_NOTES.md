# Sprint-157 Rev4 — Gemini Görsel Okuma Dayanıklılığı

Amaç: Seans Öncesi Bağlam görsel metin çıkarımında geçici Gemini servis
yoğunluğu nedeniyle oluşan HTTP 503 ve kısa süreli HTTP 429 hatalarının
kullanıcı akışını gereksiz yere kesmesini önlemek.

## Değişiklik

- Yalnız `backend/app/market_context/image_input.py` değiştirilir.
- HTTP 503 ve HTTP 429 geçici hata olarak işaretlenir.
- İlk istek başarısız olursa en fazla üç yeniden deneme yapılır.
- Bekleme planı: 2 sn -> 4 sn -> 8 sn.
- Her beklemeye en fazla 350 ms küçük jitter eklenir.
- 400/401/403 gibi kalıcı istemci/kimlik hataları yeniden denenmez.
- Tüm denemeler başarısızsa kullanıcıya:
  - servisin geçici olarak kullanılamadığı,
  - görselin arşivde korunmaya devam ettiği,
  - manuel giriş veya daha sonra yeniden deneme seçenekleri
  açık biçimde bildirilir.
- Sonsuz retry yoktur.

## Değiştirilmeyenler

- görsel arşiv sözleşmesi
- kullanıcı onayı
- `market_context_dashboard.py`
- Sprint-157 Rev3 wrapper
- Haber Merkezi
- teknik skor / AL-SAT motoru
- Gölge Portföy / Aktif Trader
- Sprint-158 dosyaları
