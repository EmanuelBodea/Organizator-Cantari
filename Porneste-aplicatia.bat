@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 app.py
    goto check
)
where python >nul 2>nul
if not errorlevel 1 (
    python app.py
    goto check
)
echo Python nu a fost gasit. Instaleaza Python 3.10+ de pe https://www.python.org/downloads/
echo La instalare bifeaza "Add python.exe to PATH".
pause
exit /b 1
:check
if errorlevel 1 (
    echo.
    echo Aplicatia s-a oprit cu o eroare. Trimite-mi mesajul afisat mai sus.
    pause
)