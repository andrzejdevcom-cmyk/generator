@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"
if errorlevel 1 (
  echo.
  echo Nie udalo sie uruchomic aplikacji. Szczegoly bledu sa powyzej.
  pause
  exit /b 1
)
