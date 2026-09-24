@echo off
rem Start the control panel website (http://localhost:8765) and open it in the browser.
cd /d "%~dp0"
title Schedule Bot - Control Panel
if not exist ".venv\Scripts\python.exe" goto :not_installed
".venv\Scripts\python.exe" -m tnio_bot.panel
echo.
echo The control panel stopped.
pause
exit /b 0

:not_installed
echo The bot is not installed yet. Double-click Install.bat first.
pause
exit /b 1
