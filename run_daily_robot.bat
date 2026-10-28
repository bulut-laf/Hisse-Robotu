@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0

echo [1/2] Gunluk piyasa ve KAP verileri cekiliyor...
python backend\app\jobs\daily_update_job.py

echo [2/2] Sistem bakimi ve disk temizligi yapiliyor...
python backend\app\jobs\db_maintenance_job.py

echo Tum sabah operasyonlari basariyla tamamlandi!
timeout /t 5 >nul