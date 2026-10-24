@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON=%CD%\.venv\Scripts\python.exe"
set "APP=%CD%\backend\mobile_dashboard.py"
set "PORT=8511"

if not exist "%PYTHON%" (
  echo HATA: Python sanal ortami bulunamadi:
  echo %PYTHON%
  pause
  exit /b 1
)

if not exist "%APP%" (
  echo HATA: Mobil panel bulunamadi:
  echo %APP%
  pause
  exit /b 1
)

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$ip=(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi' -ErrorAction SilentlyContinue ^| Where-Object {$_.IPAddress -notlike '169.254*'} ^| Select-Object -First 1 -ExpandProperty IPAddress); if(-not $ip){$ip=(Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object {$_.IPAddress -notmatch '^(127\.|169\.254\.)'} ^| Select-Object -First 1 -ExpandProperty IPAddress)}; if($ip){$ip}"`) do set "LANIP=%%I"

if not defined LANIP set "LANIP=BU-BILGISAYARIN-IP-ADRESI"

echo.
echo ============================================================
echo   HISSE ROBOTU MOBIL V1
echo ============================================================
echo Bilgisayar paneli : http://localhost:%PORT%
echo Poco / tablet     : http://%LANIP%:%PORT%
echo.
echo Telefon ve bilgisayar ayni Wi-Fi aginda olmali.
echo Windows Guvenlik Duvari sorarsa OZEL AGLAR icin izin verin.
echo Bu pencere acik kaldigi surece mobil panel calisir.
echo ============================================================
echo.

"%PYTHON%" -m streamlit run "%APP%" --server.address 0.0.0.0 --server.port %PORT% --browser.gatherUsageStats false --server.headless true
set "RC=%ERRORLEVEL%"
echo.
echo Mobil panel kapandi. Kod: %RC%
pause
exit /b %RC%
