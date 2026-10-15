@echo off
title TradeGear MT5 Windows Agent
color 0A

echo ===================================================
echo     TradeGear MT5 Windows Bridge Agent (v2.0)
echo ===================================================
echo.

:: Check python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak terdeteksi. Silakan pasang Python 3.11+ dari python.org
    pause
    exit /b
)

:: Install dependencies if needed
echo [*] Memeriksa library pendukung...
pip install -q websockets MetaTrader5 python-dotenv

:: Ask for pairing code if .env does not exist
if not exist .env (
    echo.
    echo [*] Belum ada konfigurasi .env yang tersimpan.
    set /p PAIRING_CODE="Masukkan Kode Pairing dari Website (contoh: TG-849201): "
    set /p SERVER_URL="Masukkan URL Web Server [default: wss://trade.homever.my.id/ws/agent]: "
    
    if "%SERVER_URL%"=="" set SERVER_URL=wss://trade.homever.my.id/ws/agent

    echo TRADEGEAR_SERVER_URL=%SERVER_URL% > .env
    echo TRADEGEAR_AGENT_TOKEN=%PAIRING_CODE% >> .env
    echo MT5_TICK_SYMBOLS=XAUUSD,EURUSD,GBPUSD,BTCUSD >> .env
    echo MT5_TICK_INTERVAL_MS=500 >> .env
    echo.
    echo [OK] Pengaturan tersimpan ke .env!
)

echo.
echo [*] Menghubungkan ke MetaTrader 5 dan Server TradeGear...
python -m agent.main

pause
