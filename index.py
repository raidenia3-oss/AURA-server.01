import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from upstash_vector import Index

app = FastAPI()

# --- CONFIGURACIÓN ---
vector_index = Index(
    url=os.environ.get("UPSTASH_VECTOR_REST_URL"), 
    token=os.environ.get("UPSTASH_VECTOR_REST_TOKEN")
)
OR_KEY = os.environ.get("OPENROUTER_API_KEY")

# --- INTERFAZ VISUAL (El chat que te faltaba) ---
HTML_CHAT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AURA CORE</title>
    <style>
        body { background: #0a0a0a; color: #00ff41; font-family: monospace; margin: 0; display: flex; flex-direction: column; height: 100vh; }
        #chat { flex: 1; overflow-y: auto; padding: 15px; }
        .msg { margin: 10px 0; padding: 10px; border-radius: 5px; max-width: 80%; }
        .user { align-self: flex-end; background: #002200; border: 1px solid #00ff41; margin-left: auto; }
        .aura { align-self: flex-start; background: #161616; border: 1px solid #ff0055; }
        #input-area { padding: 15px; background: #000; display: flex; gap: 10px; border-top: 1px solid #333; }
        input { flex: 1; background: #000; border: 1px solid #00ff41; color: #00ff41; padding: 10px; outline: none; }
        button { background: #00ff41; border: none; padding: 10px 20px; cursor: pointer; color: #000; font-weight: bold; }
    </style>
</head>
<body>
    <div style="text-align:center; padding:10px; border-bottom:1px solid #333;">AURA SYSTEM v2.6 [MEMORIA ACTIVA]</div>
    <div id="chat"></div>
    <div id="input-area">
        <input type="text" id="msgInput" placeholder="Escribe tu orden..." onkeypress="if(event.key==='Enter') send()">
        <button onclick="send()">ENVIAR</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('msgInput');
        async function send() {
            const val = input.value.trim();
            if(!val) return;
            chat.innerHTML += `<div class="msg user">${val}</div>`;
            input.value = '';
            chat.scrollTop = chat.scrollHeight;
            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({messages: [{role: 'user', content: val}]})
                });
                const data = await res.json();
                chat.innerHTML += `<div class="msg aura">${data.content}</div>`;
                chat.scrollTop = chat.scrollHeight;
            } catch(e) { chat.innerHTML += `<div class="msg aura">[ERROR DE ENLACE]</div>`; }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML_CHAT

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        user_query = messages[-1]['content'] if messages else ""

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}"},
            json={"model": "meta-llama/llama-3.1-8b-instruct:free", "messages": messages},
            timeout=15
        )
        respuesta = res.json()['choices'][0]['message']['content']

        if vector_index:
            try:
                vector_index.upsert(vectors=[(f"msg_{os.urandom(4).hex()}", user_query, {"res": respuesta})])
            except: pass

        return {"content": respuesta}
    except Exception as e:
        return JSONResponse(status_code=500, content={"content": f"Error: {str(e)}"})
