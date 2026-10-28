@echo off
title Hisse Robotu Terminali
echo ==========================================
echo Hisse Robotu arayuzu baslatiliyor...
echo Lutfen bu pencereyi kapatmayin.
echo ==========================================
cd /d "%~dp0"

:: Sizin orijinal PowerShell baslatici scriptinizi tetikliyoruz
powershell.exe -ExecutionPolicy Bypass -File ".\Hisse-Robotu-Baslat.ps1"