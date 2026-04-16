import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from upstash_vector import Index
from duckduckgo_search import DDGS 
import personality 

app = FastAPI()

# --- CONFIGURACION DE MEMORIA ---
try:
    vector_index = Index(
        url=os.environ.get("UPSTASH_VECTOR_REST_URL"),
        token=os.environ.get("UPSTASH_VECTOR_REST_TOKEN")
    )
except Exception:
    vector_index = None

OR_KEY = os.environ.get("OPENROUTER_API_KEY")

# --- INTERFAZ VISUAL (Protocolo AURA) ---
HTML_CHAT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AURA CORE</title>
    <style>
        body { background: #0a0a0a; color: #00ff41; font-family: monospace; margin: 0; display: flex; flex-direction: column; height: 100vh; }
        #chat { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; }
        .msg { margin: 10px 0; padding: 10px; border-radius: 5px; max-width: 85%; border: 1px solid #00ff41; box-shadow: 0 0 5px #00ff41; }
        .user { align-self: flex-end; background: #002200; }
        .aura { align-self: flex-start; background: #111; }
        #input-area { padding: 15px; background: #000; display: flex; gap: 10px; border-top: 1px solid #333; }
        input { flex: 1; background: #000; border: 1px solid #00ff41; color: #00ff41; padding: 12px; outline: none; }
        button { background: #00ff41; border: none; padding: 10px 25px; cursor: pointer; color: #000; font-weight: bold; }
    </style>
</head>
<body>
    <div style="text-align:center; padding:10px; border-bottom:1px solid #333; letter-spacing: 2px;">AURA SYSTEM v2.9 [WEB LINK ACTIVE]</div>
    <div id="chat"></div>
    <div id="input-area">
        <input type="text" id="msgInput" placeholder="Ingrese comandos de búsqueda o consulta..." onkeypress="if(event.key==='Enter') send()">
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
            } catch (e) {
                chat.innerHTML += `<div class="msg aura" style="border-color: red; color: red;"><b>AURA [ERROR]:</b> Fallo en el enlace de datos.</div>`;
            }
            chat.scrollTop = chat.scrollHeight;
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

        # --- FASE 1: BUSQUEDA WEB GRATUITA ---
        resultados_web = ""
        try:
            with DDGS() as ddgs:
                busqueda = [r for r in ddgs.text(user_query, max_results=3)]
                for r in busqueda:
                    resultados_web += f"\\n[Web] {r['title']}: {r['body']}"
        except:
            resultados_web = "Sin acceso a red externa en este ciclo."

        # --- MEMORIA HISTORICA ---
        ctx = ""
        if vector_index:
            try:
                search = vector_index.query(data=user_query, top_k=2, include_metadata=True)
                for item in search:
                    ctx += f"\\n[Memoria: {item.metadata.get('res')}]"
            except: pass

        # --- CONSTRUCCION DE PROMPT ---
        sys_content = personality.get_system_prompt(ctx, resultados_web)
        messages.insert(0, {"role": "system", "content": sys_content})

        # --- LLAMADA AL MODELO GRATUITO ESTABLE ---
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OR_KEY}",
                "HTTP-Referer": "https://aura-server-01.vercel.app",
                "X-Title": "AURA CORE"
            },
            json={
                "model": "google/gemma-2-9b-it:free", # <--- Modelo gratuito y estable
                "messages": messages,
                "temperature": 0.7
            },
            timeout=20
        )

        ans_raw = res.json()
        
        # Validar si hay errores en la respuesta de la API
        if 'choices' not in ans_raw:
            error_msg = ans_raw.get('error', {}).get('message', 'Error desconocido')
            return {"content": f"[AURA-CORE ERROR]: La API respondió: {error_msg}"}

        ans = ans_raw['choices'][0]['message']['content']

        # Guardar en memoria
        if vector_index:
            try:
                vector_index.upsert(vectors=[(f"msg_{os.urandom(4).hex()}", user_query, {"res": ans})])
            except: pass

        return {"content": ans}

    except Exception as e:
        return JSONResponse(status_code=500, content={"content": f"[FALLO CRITICO]: {str(e)}"})
