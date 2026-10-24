HISSE ROBOTU - SPRINT 40 TEK KOMUTLU KURULUM VE TEST

1. ZIP'i doğrudan şu klasöre ayıklayın:
   D:\Projects\Hisse-Robotu

2. Hedef testi çalıştırın:
   python -m pytest .\backend\tests\test_sprint_package_runner.py -q

Beklenen:
6 passed

3. Tam regresyon:
   python -m pytest -q

Beklenen toplam:
696 passed

KULLANIM

Hızlı mod:
.\Sprint-Paketini-Kur-ve-Test-Et.ps1 -Mod Hizli -HedefTest ".\backend\tests\test_ornek.py"

Tam mod:
.\Sprint-Paketini-Kur-ve-Test-Et.ps1 -Mod Tam

ZIP paketini çıkarıp hedef test çalıştırma:
.\Sprint-Paketini-Kur-ve-Test-Et.ps1 -Mod Hizli -Paket "C:\Yol\Sprint.zip" -HedefTest ".\backend\tests\test_ornek.py"

ZIP paketini çıkarıp tam regresyon çalıştırma:
.\Sprint-Paketini-Kur-ve-Test-Et.ps1 -Mod Tam -Paket "C:\Yol\Sprint.zip"
