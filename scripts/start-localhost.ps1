# scripts/start-localhost.ps1

Write-Host "AURA Localhost Startup" -ForegroundColor Cyan
Write-Host ""

# Detectar IP local (WiFi)
$ipLine = (ipconfig | Select-String "IPv4 Address" | Select-Object -First 1)
$localIP = ""
if ($ipLine) {
    $localIP = ($ipLine.Line -replace '.*?:\s*' -replace '\s*$' -replace '[^0-9.]')
}

Write-Host "Starting services..." -ForegroundColor Yellow
Write-Host ""

# 1. ame_backend en :8000
Write-Host "Starting ame_backend (localhost:8000)..." -ForegroundColor Yellow
$backendProcess = Start-Process -NoNewWindow -PassThru -FilePath "python" `
    -ArgumentList "ame_backend/src/main.py" -WorkingDirectory $PWD
Write-Host "  Backend PID: $($backendProcess.Id)" -ForegroundColor Green

# Esperar a que el backend este listo
Start-Sleep -Seconds 5

# 2. Frontend en :3000 (usa .env.local.dev como NODE_ENV=development)
Write-Host "Starting frontend (localhost:3000)..." -ForegroundColor Yellow
$frontendProcess = Start-Process -NoNewWindow -PassThru -FilePath "npm" `
    -ArgumentList "run", "dev" -WorkingDirectory "frontend" `
    -EnvironmentVariables @{"NODE_ENV" = "development"}
Write-Host "  Frontend PID: $($frontendProcess.Id)" -ForegroundColor Green

# Esperar a que el frontend este listo
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "All services started!" -ForegroundColor Green
Write-Host ""
Write-Host "URLs:" -ForegroundColor Cyan
Write-Host "  Frontend (Local):  http://localhost:3000" -ForegroundColor White
if ($localIP) { Write-Host "  Frontend (WiFi):   http://$localIP`:3000" -ForegroundColor White }
Write-Host "  Backend  (Local):  http://localhost:8000" -ForegroundColor White
if ($localIP) { Write-Host "  Backend  (WiFi):   http://$localIP`:8000" -ForegroundColor White }
Write-Host "  Health Check:       http://localhost:8000/api/health" -ForegroundColor White
Write-Host ""
Write-Host "Ctrl+C no detiene estos procesos. Para detenerlos:" -ForegroundColor Yellow
Write-Host "  Stop-Process -Id $($backendProcess.Id), $($frontendProcess.Id) -Force" -ForegroundColor White
Write-Host ""

# Mantener la ventana abierta hasta que el usuario pulse Enter
$null = Read-Host "Press Enter to close this window (services keep running)"

# Al cerrar la ventana, detener los procesos iniciados aqui.
Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
Write-Host "Services stopped." -ForegroundColor Green
