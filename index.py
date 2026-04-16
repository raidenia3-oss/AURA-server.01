import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

OR_KEY = os.environ.get("OPENROUTER_API_KEY")

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h1>AURA Online</h1>"

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    res = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OR_KEY}"},
        json={"model": "meta-llama/llama-3.1-8b-instruct:free", "messages": messages}
    )
    return res.json()
