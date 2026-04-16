import os
import requests
import personality
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from upstash_vector import Index
from duckduckgo_search import DDGS

app = FastAPI()

# --- CONFIGURACION ---
try:
    vector_index = Index(
        url=os.environ.get("UPSTASH_VECTOR_REST_URL"),
        token=os.environ.get("UPSTASH_VECTOR_REST_TOKEN")
    )
except Exception:
    vector_index = None

OR_KEY = os.environ.get("OPENROUTER_API_KEY")

def web_search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        summary = ""
        for r in results:
            summary += f"\n[Web] {r.get('title')}: {r.get('body')}"
        return summary
    except:
        return ""

# Copia aquí el bloque HTML_CHAT que pasaste (es muy bueno y funciona bien)
# Solo asegúrate de pegarlo sin puntos rojos.
HTML_CHAT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AURA CORE</title>
    <style>
        * { box-sizing: border-box; }
        body { background: #0a0a0a; color: #00ff41; font-family: monospace; margin: 0; display: flex; flex-direction: column; height: 100vh; }
        #header { text-align:center; padding:10px; border-bottom:1px solid #333; display:flex; justify-content:center; align-items:center; gap:15px; }
        #status { font-size:11px; color:#555; }
        #status.active { color:#00ff41; }
        #chat { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; }
        .msg { margin: 10px 0; padding: 10px; border-radius: 5px; max-width: 85%; border: 1px solid #00ff41; white-space: pre-wrap; }
        .user { align-self: flex-end; background: #002200; }
        .aura { align-self: flex-start; background: #111; }
        .system { align-self: center; background: #001100; border-color:#333; font-size:11px; color:#555; max-width:100%; }
        #input-area { padding: 15px; background: #000; display: flex; gap: 8px; border-top: 1px solid #333; flex-wrap: wrap; }
        input[type=text] { flex: 1; min-width: 200px; background: #000; border: 1px solid #00ff41; color: #00ff41; padding: 12px; outline: none; }
        button { background: #00ff41; border: none; padding: 10px 18px; cursor: pointer; color: #000; font-weight: bold; font-family: monospace; }
        button:hover { background: #00cc33; }
        button.active { background: #ff4444; color: #fff; }
        #file-area { width:100%; display:flex; gap:8px; align-items:center; }
        #file-name { font-size:11px; color:#555; }
    </style>
</head>
<body>
    <div id="header">
        <span>AURA SYSTEM v3.1</span>
        <div id="status">● STANDBY</div>
    </div>
    <div id="chat">
        <div class="msg system">Vínculo establecido. Fase 1, 2 y 5 activas.</div>
    </div>
    <div id="input-area">
        <div id="file-area">
            <input type="file" id="fileInput" accept=".cpp,.c,.py,.txt,.js,.ts,.md,.json" style="display:none" onchange="handleFile()">
            <button onclick="document.getElementById('fileInput').click()">📎 ARCHIVO</button>
            <span id="file-name">Sin archivo</span>
            <button id="clearFile" onclick="clearFile()" style="display:none; background:#111; color:#ff4444; border:1px solid #ff4444; padding:5px 10px;">✕</button>
        </div>
        <input type="text" id="msgInput" placeholder="Ordenes... (usa 'busca:' para red)" onkeypress="if(event.key==='Enter') send()">
        <button onclick="send()">EJECUTAR</button>
        <button id="voiceBtn" onclick="toggleVoice()">🎤 VOZ</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('msgInput');
        const status = document.getElementById('status');
        let fileContent = null;
        let fileName = null;
        let isListening = false;
        let recognition = null;

        function handleFile() {
            const file = document.getElementById('fileInput').files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (e) => {
                fileContent = e.target.result;
                fileName = file.name;
                document.getElementById('file-name').textContent = '📄 ' + fileName;
                document.getElementById('clearFile').style.display = 'inline';
            };
            reader.readAsText(file);
        }

        function clearFile() {
            fileContent = null;
            fileName = null;
            document.getElementById('file-name').textContent = 'Sin archivo';
            document.getElementById('clearFile').style.display = 'none';
            document.getElementById('fileInput').value = '';
        }

        function toggleVoice() {
            if (!('webkitSpeechRecognition' in window)) { alert('Usa Chrome'); return; }
            if (isListening) { recognition.stop(); return; }
            recognition = new webkitSpeechRecognition();
            recognition.lang = 'es-ES';
            recognition.onstart = () => { 
                isListening = true; 
                document.getElementById('voiceBtn').classList.add('active');
                status.textContent = '● ESCUCHANDO';
            };
            recognition.onresult = (e) => { input.value = e.results[0][0].transcript; send(); };
            recognition.onend = () => { 
                isListening = false; 
                document.getElementById('voiceBtn').classList.remove('active');
                status.textContent = '● STANDBY';
            };
            recognition.start();
        }

        function speak(text) {
            if (!('speechSynthesis' in window)) return;
            window.speechSynthesis.cancel();
            const utt = new SpeechSynthesisUtterance(text.replace(/[*#`]/g, '').substring(0, 250));
            utt.lang = 'es-ES';
            window.speechSynthesis.speak(utt);
        }

        function addMsg(type, text, used_search, used_file) {
            const div = document.createElement('div');
            div.className = 'msg ' + type;
            let meta = "";
            if(used_search) meta += " <small style='color:#0066ff'>[🌐 Red]</small>";
            if(used_file) meta += " <small style='color:#ff6600'>[📄 Archivo]</small>";
            div.innerHTML = `<b>${type === 'aura' ? 'AURA' : 'Raiden'}:</b>${meta}<br>${text}`;
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        async function send() {
            const val = input.value.trim();
            if (!val) return;
            input.value = '';
            addMsg('user', val + (fileName ? ` (Doc: ${fileName})` : ''), false, false);
            status.textContent = '● PROCESANDO';
            
            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages: [{ role: 'user', content: val }],
                        file_content: fileContent,
                        file_name: fileName
                    })
                });
                const data = await res.json();
                addMsg('aura', data.content, data.used_search, data.used_file);
                speak(data.content);
            } catch(e) { addMsg('aura', 'Error de conexión nuclear.', false, false); }
            status.textContent = '● STANDBY';
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
        file_content = data.get("file_content")
        file_name = data.get("file_name")
        user_query = messages[-1]['content'] if messages else ""

        used_search = False
        used_file = False

        # Contexto de Archivo
        file_ctx = ""
        if file_content:
            used_file = True
            file_ctx = f"\n[Lectura de Archivo {file_name}]:\n{file_content[:5000]}"

        # Búsqueda Web
        web_ctx = ""
        keywords = ["busca:", "qué es", "precio", "noticias", "error", "actual"]
        if any(k in user_query.lower() for k in keywords):
            used_search = True
            web_ctx = web_search(user_query.replace("busca:", ""))

        # Memoria
        mem_ctx = ""
        if vector_index:
            try:
                search = vector_index.query(data=user_query, top_k=1, include_metadata=True)
                for item in search: mem_ctx = f"\n[Memoria]: {item.metadata.get('res')}"
            except: pass

        # Inyectar prompt de sistema modular
        messages.insert(0, {"role": "system", "content": personality.get_system_prompt(mem_ctx, file_ctx, web_ctx)})

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}"},
            json={"model": "openrouter/free", "messages": messages},
            timeout=25
        )

        ans_raw = res.json()
        ans = ans_raw['choices'][0]['message']['content']

        # Guardar en memoria
        if vector_index:
            try: vector_index.upsert(vectors=[(f"msg_{os.urandom(2).hex()}", user_query, {"res": ans})])
            except: pass

        return {"content": ans, "used_search": used_search, "used_file": used_file}

    except Exception as e:
        return JSONResponse(status_code=500, content={"content": f"Fallo en el Nexo: {str(e)}"})
