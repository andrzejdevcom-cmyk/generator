@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
if errorlevel 1 (
  echo.
  echo Instalacja nie powiodla sie. Szczegoly bledu sa powyzej.
  pause
  exit /b 1
)
echo.
echo Gotowe. Uruchom start.bat.
pause
