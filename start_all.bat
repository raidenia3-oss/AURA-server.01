@echo off
cd /d "c:\Users\User\Downloads\AURA"
setlocal enabledelayedexpansion

echo ============================================
echo   AURA — Unified Startup
echo ============================================

:: 1. Ollama
echo [1/4] Starting Ollama...
start /b "" "ollama serve"

:: 2. Wait for Ollama
echo [2/4] Waiting for Ollama health...
python AURA_Core\check_health.py

:: 3. Flask Backend (puerto 5000)
echo [3/4] Starting AME Flask Server...
start /b "" python AME_Core\servidor_ame.py

:: Pausa breve para que Flask termine de cargar
timeout /t 3 /nobreak >nul

:: 4. Proxy Dashboard (puerto 8080)
echo [4/4] Starting AME Client (Proxy)...
start /b "" python AME_Core\ame_client.py

echo.
echo ============================================
echo  ✅ ALL SERVICES RUNNING
echo  📊 Dashboard:   http://localhost:8080
echo  🔧 API Status:  http://localhost:5000/api/status
echo  🧠 Ollama:      http://localhost:11434
echo ============================================
echo  (Cierra con: taskkill /f /im python.exe)
echo ============================================
endlocal