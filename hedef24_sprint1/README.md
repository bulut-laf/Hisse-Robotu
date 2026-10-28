# Hedef 24 — Sprint 1 başlangıç verisi

Bu paket yalnızca 24 kayıtlık başlangıç JSON dosyasını kurar. Dashboard, Erste Hungary F1–F4 ve AL-SAT koduna dokunmaz.

PowerShell proje kökünde:
```powershell
.\INSTALL_HEDEF24_SPRINT1.ps1
```
Hedef dosya: `_discovery\erste_hungary\hedef24_portfolio_seed.json`

İlk 9 ISIN ve K/Z yüzdeleri kullanıcının verdiği önceki tablodan alınmıştır. K/Z yüzdeleri güncel piyasa verisi olarak doğrulanmamıştır. Kalan ISIN, maliyet, fiyat, sinyal ve valör alanları boştur. `execution_authority` = `NONE`; işlem gerçekleştirmez.
