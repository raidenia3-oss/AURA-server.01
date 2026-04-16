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

# --- INTERFAZ VISUAL ---
HTML_CHAT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AURA CORE</title>
    <style>
        body { background: #0a0a0a; color: #00ff41; font-family: monospace; margin: 0; display: flex; flex-direction: column; height: 100vh; }
        #chat { flex: 1; overflow-y: auto; padding: 15px; border-bottom: 1px solid #1a1a1a; }
        .msg { margin: 10px 0; padding: 10px; border-radius: 5px; max-width: 85%; line-height: 1.4; }
        .user { align-self: flex-end; background: #002200; border: 1px solid #00ff41; margin-left: auto; color: #fff; }
        .aura { align-self: flex-start; background: #111; border: 1px solid #00ff41; box-shadow: 0 0 10px rgba(0,255,65,0.2); }
        #input-area { padding: 15px; background: #000; display: flex; gap: 10px; }
        input { flex: 1; background: #000; border: 1px solid #00ff41; color: #00ff41; padding: 12px; outline: none; font-family: monospace; }
        button { background: #00ff41; border: none; padding: 10px 25px; cursor: pointer; color: #000; font-weight: bold; font-family: monospace; }
        button:hover { background: #00cc33; }
    </style>
</head>
<body>
    <div style="text-align:center; padding:10px; border-bottom:1px solid #333; font-size: 0.8em; letter-spacing: 2px;">AURA SYSTEM v2.7 [PROTOCOL: CORTANA/JARVIS]</div>
    <div id="chat" style="display: flex; flex-direction: column;"></div>
    <div id="input-area">
        <input type="text" id="msgInput" placeholder="Esperando órdenes..." onkeypress="if(event.key==='Enter') send()">
        <button onclick="send()">EJECUTAR</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('msgInput');
        async function send() {
            const val = input.value.trim();
            if(!val) return;
            chat.innerHTML += `<div class="msg user"><b>Raiden:</b><br>${val}</div>`;
            input.value = '';
            chat.scrollTop = chat.scrollHeight;
            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({messages: [{role: 'user', content: val}]})
                });
                const data = await res.json();
                chat.innerHTML += `<div class="msg aura"><b>AURA:</b><br>${data.content}</div>`;
                chat.scrollTop = chat.scrollHeight;
            } catch(e) { chat.innerHTML += `<div class="msg aura">[ERROR EN EL NEXO DE DATOS]</div>`; }
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

        # --- RECUPERACIÓN DE MEMORIA ---
        memoria_contexto = ""
        if vector_index:
            try:
                # Busca registros pasados similares a la consulta actual
                search = vector_index.query(data=user_query, top_k=2, include_metadata=True)
                for item in search:
                    memoria_contexto += f"\n[Dato recuperado: {item.metadata.get('res')}]"
            except: pass

        # --- SYSTEM PROMPT (IDENTIDAD) ---
        system_prompt = {
            "role": "system",
            "content": (
                "Eres AURA, una IA de soporte táctico y técnico para Raiden. "
                "Tu personalidad es una combinación de Cortana y Jarvis: eficiente, analítica, "
                "ligeramente irónica y siempre profesional. Habla siempre en español. "
                "Eres experta en C++, sistemas y hardware. No menciones estudios o universidades "
                "a menos que el usuario lo haga. Usa el contexto recordado para ser más útil."
                f"{memoria_contexto}"
            )
        }
        messages.insert(0, system_prompt)

        # --- LLAMADA A OPENROUTER ---
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}"},
            json={
                "model": "meta-llama/llama-3.1-8b-instruct:free", 
                "messages": messages
            },
            timeout=15
        )
        respuesta = res.json()['choices'][0]['message']['content']

        # --- GUARDAR EN MEMORIA ---
        if vector_index:
            try:
                vector_index.upsert(vectors=[(f"msg_{os.urandom(4).hex()}", user_query, {"res": respuesta})])
            except: pass

        return {"content": respuesta}
    except Exception as e:
        return JSONResponse(status_code=500, content={"content": f"Fallo en el protocolo: {str(e)}"})
