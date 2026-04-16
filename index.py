import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

# Tu llave que ya configuraste en las variables de Vercel
OR_KEY = os.environ.get("OPENROUTER_API_KEY")

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h1>AURA Online - Sistema Listo</h1>"

@app.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        
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
