@echo off
title SecureDocs Server
cd /d "%~dp0"
echo ========================================================
echo               SecureDocs Application Server
echo ========================================================
echo.
echo Starting SecureDocs on http://localhost:5000 ...
echo [Tip] Keep this window open so the website stays online!
echo.
python run.py
if errorlevel 1 (
    echo.
    echo Server stopped with error.
    pause
)
