# Sprint-135 Rev1 — Toplu Tarihsel Export Ana Dashboard Entegrasyonu

Momentum Keşif ekranına gerçek MomentumWalkForwardService tabanlı toplu tarihsel tarama bağlanır.

Kullanıcı akışı:
- Toplu tarihsel tarama ve CSV export
- Başlangıç / bitiş tarihi
- BIST100 / BIST Tüm
- Birleşik CSV
- İsteğe bağlı günlük ZIP

Kurulum dashboard.py dosyasını önce yedekler; yalnız tekil anchor'lar bulunursa patch uygular.
Patch/compile/hedef test başarısız olursa dashboard otomatik geri yüklenir.


## Rev1 düzeltmesi
Hedef testin `tools` paket import bağımlılığı kaldırıldı; patch helper proje içindeki `backend.app.ui` altında import edilebilir hale getirildi.
