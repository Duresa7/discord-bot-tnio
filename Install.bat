@echo off
rem One-click install for the Schedule Bot. Safe to run again at any time.
setlocal
cd /d "%~dp0"
title Schedule Bot - Install
echo.
echo  === Schedule Bot: install ===
echo.

rem --- 1. Python ---
where py >nul 2>nul
if errorlevel 1 goto :no_python

rem --- 2. Git, for the Update button ---
where git >nul 2>nul
if not errorlevel 1 goto :have_git
echo Installing Git. This needs the internet and can take a few minutes...
winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :no_git
echo.
echo Git is installed. Close this window and double-click Install.bat again.
pause
exit /b 0
:have_git

rem --- 3. Connect this folder to GitHub, if it came from a ZIP download ---
if exist ".git" goto :have_repo
echo Connecting this folder to GitHub...
git init -q -b main || goto :failed
git remote add origin https://github.com/Duresa7/discord-bot-tnio.git || goto :failed
git fetch -q origin main || goto :failed
git reset -q --hard origin/main || goto :failed
git branch -q --set-upstream-to=origin/main main || goto :failed
:have_repo

rem --- 4. Python environment and packages ---
if exist ".venv\Scripts\python.exe" goto :have_venv
echo Making the Python environment...
py -3 -m venv .venv || goto :failed
:have_venv
echo Installing packages. This can take a few minutes...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt || goto :failed

rem --- 5. Local files (never overwritten) ---
if not exist ".env" copy ".env.example" ".env" >nul
if not exist "data\hosts.csv" copy "data\hosts.example.csv" "data\hosts.csv" >nul

echo.
echo  Done! Next steps:
echo    1. Put credentials.json in this folder.
echo    2. Double-click "Start Control Panel.bat".
echo.
pause
exit /b 0

:no_python
echo Python is not installed.
echo The download page opens now. Install Python and check the box "Add python.exe to PATH".
echo Then double-click Install.bat again.
start "" https://www.python.org/downloads/
pause
exit /b 1

:no_git
echo Git could not be installed automatically.
echo The download page opens now. Install Git, then double-click Install.bat again.
start "" https://git-scm.com/download/win
pause
exit /b 1

:failed
echo.
echo Something went wrong. Take a screenshot of this window and send it to the bot owner.
pause
exit /b 1
