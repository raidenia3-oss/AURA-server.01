# scripts/check-local.ps1

Write-Host "AURA Localhost Health Check" -ForegroundColor Cyan
Write-Host ""

# Detectar IP local (WiFi)
$ipLine = (ipconfig | Select-String "IPv4 Address" | Select-Object -First 1)
$localIP = ""
if ($ipLine) {
    $localIP = ($ipLine.Line -replace '.*?:\s*' -replace '\s*$' -replace '[^0-9.]')
}
Write-Host "Local Network IP: $localIP" -ForegroundColor Yellow
Write-Host ""

# Frontend
Write-Host -NoNewline "Frontend (localhost:3000): "
try {
    $null = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 3 -UseBasicParsing
    Write-Host "OK" -ForegroundColor Green
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}

# Backend health
Write-Host -NoNewline "Backend (localhost:8000/api/health): "
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 3 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "OK" -ForegroundColor Green
    } else {
        Write-Host "HTTP $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "FAIL" -ForegroundColor Red
}

# Archivos de configuracion locales
Write-Host -NoNewline "Config (.env files): "
if ((Test-Path "frontend/.env.local.dev") -and (Test-Path "backend/.env.local") -and (Test-Path "ame_backend/.env.local")) {
    Write-Host "OK" -ForegroundColor Green
} else {
    Write-Host "FAIL (faltan archivos)" -ForegroundColor Red
}

Write-Host ""
Write-Host "URLs:" -ForegroundColor Yellow
Write-Host "  Local:  http://localhost:3000" -ForegroundColor White
if ($localIP) { Write-Host "  WiFi:   http://$localIP`:3000" -ForegroundColor White }
Write-Host "  API:    http://localhost:8000/api/health" -ForegroundColor White
Write-Host ""
