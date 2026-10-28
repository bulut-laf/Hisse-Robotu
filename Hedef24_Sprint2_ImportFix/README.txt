Hedef24 Sprint 2 — import düzeltmesi

1. ZIP'i D:\Projects\Hisse-Robotu içine çıkarın.
2. PowerShell'de proje köküne geçin:
   cd D:\Projects\Hisse-Robotu
3. Düzeltmeyi çalıştırın:
   .\Hedef24_Sprint2_ImportFix\FIX_HEDEF24_SPRINT2_IMPORT.ps1
4. Ardından hedef doğrulamayı çalıştırın:
   .\.venv\Scripts\python.exe -m py_compile backend\app\funds\hedef24_store.py
   .\.venv\Scripts\python.exe -m pytest backend\tests\test_hedef24_store_sprint2.py -q

Yalnızca test dosyasındaki import satırını düzeltir; dashboard.py ve portföy verisine dokunmaz.
Test dosyasının değişiklik öncesi yedeğini oluşturur.
