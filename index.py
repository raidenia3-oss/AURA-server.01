import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

# Carga de Keys desde el sistema
OR_KEY = os.environ.get("OPENROUTER_API_KEY")
GROQ_KEY = os.environ.get("GROQ_API_KEY")
W_PHONE = os.environ.get("WHATSAPP_PHONE")
W_KEY = os.environ.get("WHATSAPP_API_KEY")

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h1>Servidor AURA Activo - Sistema Reestablecido</h1>"

@app.post("/api/chat")
async def chat(request: Request):
    # Aquí va la lógica de procesamiento que reconstruiremos paso a paso
    pass
