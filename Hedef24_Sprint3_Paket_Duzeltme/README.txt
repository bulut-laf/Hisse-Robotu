Hedef24 Sprint 3 kurulum düzeltmesi

Önceki installer, dashboard.py içindeki Erste Hungary bloğunun birebir metin eşleşmesine bağlı olduğu için güvenli biçimde durdu. Bu sürüm bölgeyi regex ile bulur ve yalnızca tek eşleşme varsa değiştirir; eşleşme belirsizse dashboard.py'ye dokunmaz.

1. ZIP'i D:\Projects\Hisse-Robotu içine çıkarın.
2. PowerShell'de proje kökünde çalıştırın:
   .\Hedef24_Sprint3_Paket_Duzeltme\INSTALL_HEDEF24_SPRINT3_FIX.ps1
3. Installer'ın yazdırdığı py_compile ve pytest komutlarını çalıştırın.

Her hedef dosyanın mevcut sürümü yedeklenir. Hedef 24 JSON portföy dosyası değiştirilmez. AL-SAT otomatik emir gönderimi yoktur.
