import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

# --- CONFIGURACIÓN DE CONEXIONES ---
# Estas son las llaves que pusiste en las Variables Ambientales de Vercel
OR_KEY = os.environ.get("OPENROUTER_API_KEY")
UPSTASH_URL = os.environ.get("UPSTASH_VECTOR_REST_URL")
UPSTASH_TOKEN = os.environ.get("UPSTASH_VECTOR_REST_TOKEN")

@app.get("/", response_class=HTMLResponse)
async def home():
    # Este es el mensaje que ves ahora en el navegador
    return "<h1>AURA Online - Sistema Completo</h1><p>IA y Memoria Vectorial activas.</p>"

@app.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        
        # 1. Lógica de Memoria (Opcional por ahora)
        # Aquí AURA consultará en Upstash antes de responder
        
        # 2. Lógica de IA (OpenRouter)
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}"},
            json={
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": messages
            }
        )
        return response.json()
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
