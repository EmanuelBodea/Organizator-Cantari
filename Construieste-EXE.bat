@echo off
setlocal
cd /d "%~dp0"
title Construire EXE - Organizator Cantari Betel Padureni
where py >nul 2>nul
if not errorlevel 1 (set "PY=py -3") else (set "PY=python")
%PY% --version >nul 2>nul
if errorlevel 1 (echo Python nu este instalat.& pause & exit /b 1)
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 goto fail
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name "Organizator-Cantari-Betel-Padureni" app.py
if errorlevel 1 goto fail
copy /Y "update_config.json" "dist\update_config.json" >nul
explorer "%~dp0dist"
echo EXE creat! Configurarea actualizarii este in update_config.json
pause
exit /b 0
:fail
echo Construirea a esuat.
pause
exit /b 1