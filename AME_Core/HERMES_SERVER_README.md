# Hermes Server - API Local para AURA

Este servidor expone Hermes Agent a través de una API HTTP local que puede ser accedida desde Vercel/Railway.

## Instalación y Configuración

### 1. Instalar dependencias en WSL2/Ubuntu
```bash
pip install flask requests
```

### 2. Configurar variables de entorno (opcional)
```bash
export HERMES_PATH="/home/raiden/.local/bin/hermes"
export OLLAMA_HOST="http://127.0.0.1:11434"
```

### 3. Ejecutar el servidor
```bash
python hermes_server.py
```

El servidor se ejecutará en `http://127.0.0.1:5000`

## Endpoints

### GET /health
Verifica el estado del servidor y dependencias.

**Respuesta exitosa:**
```json
{
  "status": "healthy",
  "ollama": "running",
  "hermes_path": "/home/raiden/.local/bin/hermes",
  "hermes_exists": true,
  "ollama_host": "http://127.0.0.1:11434"
}
```

### POST /ask
Envía una pregunta a Hermes y recibe la respuesta.

**Request:**
```json
{
  "prompt": "Tu pregunta aquí"
}
```

**Respuesta exitosa:**
```json
{
  "response": "Respuesta de Hermes aquí"
}
```

## Verificación

### Ejecutar pruebas
```bash
python test_hermes_server.py
```

### Verificar manualmente
```bash
# Health check
curl http://127.0.0.1:5000/health

# Probar pregunta
curl -X POST http://127.0.0.1:5000/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hola, ¿cómo estás?"}'
```

## Solución de problemas

### Error: "Ollama no está corriendo"
- Asegúrate de que Ollama esté ejecutándose en Windows
- Verifica que el puerto 11434 esté accesible desde WSL2

### Error: "Hermes no encontrado"
- El servidor automáticamente usará Ollama directamente como fallback
- Si quieres usar Hermes específicamente, instala Hermes y configura `HERMES_PATH`

### El servidor no responde
- Verifica que estés ejecutando el servidor en WSL2
- Asegúrate de que el puerto 5000 no esté ocupado
- Revisa los logs del servidor para errores

## Integración con Vercel/Railway

1. Configura ngrok apuntando al puerto 5000
2. Agrega la variable `HERMES_NGROK_URL` en Vercel/Railway
3. El endpoint `/test-hermes` en tu app de Vercel probará la conexión

## Logs

El servidor muestra información detallada al iniciar:
- ✅ Ollama: OK/No responde
- ✅ Hermes: Encontrado/No encontrado
- 📍 Puerto: 5000