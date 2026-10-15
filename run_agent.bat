@echo off
title TradeGear MT5 Bridge Agent
color 0A
echo ========================================================
echo  TradeGear - MetaTrader 5 Bridge Agent
echo ========================================================
echo.
cd /d "%~dp0mt5-agent"
set PYTHONPATH=.
"..\backend\.venv\Scripts\python.exe" -m agent.main
if errorlevel 1 (
    echo.
    echo [ERROR] Agent stopped with error.
    pause
)
