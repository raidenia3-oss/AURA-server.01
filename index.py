import os
import requests
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

# --- BUSQUEDA DUCKDUCKGO (sin API key, gratis) ---
def web_search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        summary = ""
        for r in results:
            summary += f"\n[Web] {r.get('title')}: {r.get('body')}"
        return summary
    except Exception as e:
        return ""

# --- INTERFAZ VISUAL ---
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
        .tag { font-size:10px; padding:2px 6px; border:1px solid #333; color:#555; margin-left:5px; }
        .tag.search { border-color:#0066ff; color:#0066ff; }
        .tag.file { border-color:#ff6600; color:#ff6600; }
    </style>
</head>
<body>
    <div id="header">
        <span>AURA SYSTEM v3.1</span>
        <span id="status">● STANDBY</span>
    </div>
    <div id="chat">
        <div class="msg system">Sistema iniciado. Sin límites de búsqueda. DuckDuckGo activo.</div>
    </div>
    <div id="input-area">
        <div id="file-area">
            <input type="file" id="fileInput" accept=".cpp,.c,.py,.txt,.js,.ts,.md,.json" style="display:none" onchange="handleFile()">
            <button onclick="document.getElementById('fileInput').click()">📎 ARCHIVO</button>
            <span id="file-name">Sin archivo</span>
            <button id="clearFile" onclick="clearFile()" style="display:none; background:#111; color:#ff4444; border:1px solid #ff4444; padding:5px 10px;">✕</button>
        </div>
        <input type="text" id="msgInput" placeholder="Ordenes... (usa 'busca:' para búsqueda web)" onkeypress="if(event.key==='Enter') send()">
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
                addMsg('system', `Archivo cargado: ${fileName} (${fileContent.length} caracteres)`);
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
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                alert('Usa Chrome para reconocimiento de voz.');
                return;
            }
            if (isListening) { recognition.stop(); return; }
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = 'es-ES';
            recognition.onstart = () => {
                isListening = true;
                document.getElementById('voiceBtn').classList.add('active');
                document.getElementById('voiceBtn').textContent = '🔴 ESCUCHANDO';
                status.textContent = '● ESCUCHANDO...';
                status.className = 'active';
            };
            recognition.onresult = (e) => {
                input.value = e.results[0][0].transcript;
                send();
            };
            recognition.onend = () => {
                isListening = false;
                document.getElementById('voiceBtn').classList.remove('active');
                document.getElementById('voiceBtn').textContent = '🎤 VOZ';
            };
            recognition.start();
        }

        function speak(text) {
            if (!('speechSynthesis' in window)) return;
            window.speechSynthesis.cancel();
            const clean = text.replace(/\[.*?\]/g, '').replace(/[*#`]/g, '').substring(0, 300);
            const utt = new SpeechSynthesisUtterance(clean);
            utt.lang = 'es-ES';
            utt.rate = 1.1;
            const voices = window.speechSynthesis.getVoices();
            const femVoice = voices.find(v => v.lang.startsWith('es') && (v.name.includes('Paulina') || v.name.includes('Monica') || v.name.includes('Laura')))
                          || voices.find(v => v.lang.startsWith('es'));
            if (femVoice) utt.voice = femVoice;
            utt.onstart = () => { status.textContent = '● HABLANDO'; status.className = 'active'; };
            utt.onend = () => { status.textContent = '● STANDBY'; status.className = ''; };
            window.speechSynthesis.speak(utt);
        }

        function addMsg(type, text, tags=[]) {
            const div = document.createElement('div');
            div.className = 'msg ' + type;
            let tagsHtml = tags.map(t => `<span class="tag ${t.cls}">${t.label}</span>`).join('');
            if (type === 'aura') {
                div.innerHTML = `<b>AURA:</b>${tagsHtml}<br>${text.replace(/\n/g, '<br>')}`;
            } else if (type === 'user') {
                div.innerHTML = `<b>Raiden:</b><br>${text}`;
            } else {
                div.textContent = text;
            }
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        async function send() {
            const val = input.value.trim();
            if (!val) return;
            input.value = '';
            let displayText = val;
            if (fileName) displayText += ` [📄 ${fileName}]`;
            addMsg('user', displayText);
            status.textContent = '● PROCESANDO';
            status.className = 'active';
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
                const tags = [];
                if (data.used_search) tags.push({cls:'search', label:'🌐 DDG'});
                if (data.used_file) tags.push({cls:'file', label:'📄 ARCHIVO'});
                addMsg('aura', data.content, tags);
                speak(data.content);
            } catch(e) {
                addMsg('system', 'Error de conexión: ' + e.message);
            }
            status.textContent = '● STANDBY';
            status.className = '';
        }

        window.speechSynthesis.onvoiceschanged = () => { window.speechSynthesis.getVoices(); };
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

        # --- CONTEXTO DE ARCHIVO ---
        file_ctx = ""
        if file_content and file_name:
            used_file = True
            file_ctx = f"\n\n[ARCHIVO ADJUNTO: {file_name}]\n```\n{file_content[:8000]}\n```"

        # --- MEMORIA VECTORIAL ---
        mem_ctx = ""
        if vector_index:
            try:
                search = vector_index.query(data=user_query, top_k=2, include_metadata=True)
                for item in search:
                    mem_ctx += f"\n[Memoria: {item.metadata.get('res')}]"
            except:
                pass

        # --- BUSQUEDA WEB AUTOMATICA ---
        web_ctx = ""
        keywords = ["busca:", "buscar", "qué es", "que es", "cómo", "como", "precio",
                    "noticias", "hoy", "actual", "último", "ultimo", "2024", "2025", "2026",
                    "error", "solución", "solucion", "tutorial", "github", "cuánto", "cuanto"]
        should_search = any(k in user_query.lower() for k in keywords) or user_query.lower().startswith("busca:")
        clean_query = user_query.replace("busca:", "").strip()

        if should_search:
            web_ctx = web_search(clean_query)
            if web_ctx:
                used_search = True

        # --- PROMPT DE SISTEMA ---
        sys_msg = {
            "role": "system",
            "content": f"Eres AURA, IA personal de Raiden (estilo Cortana/Jarvis). Experta en C++, tecnología y hardware. Habla español, sé concisa y directa.{mem_ctx}{file_ctx}{web_ctx}"
        }
        messages.insert(0, sys_msg)

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OR_KEY}",
                "HTTP-Referer": "https://aura-server-01.vercel.app",
                "X-Title": "AURA"
            },
            json={"model": "openrouter/free", "messages": messages},
            timeout=20
        )

        ans_raw = res.json()
        if 'choices' not in ans_raw:
            return JSONResponse(status_code=500, content={"content": f"[ERROR API]: {ans_raw}", "used_search": False, "used_file": False})

        ans = ans_raw['choices'][0]['message']['content']

        if vector_index:
            try:
                vector_index.upsert(vectors=[(f"msg_{os.urandom(4).hex()}", user_query, {"res": ans})])
            except:
                pass

        return {"content": ans, "used_search": used_search, "used_file": used_file}

    except Exception as e:
        return JSONResponse(status_code=500, content={"content": f"[EXCEPCION]: {str(e)}", "used_search": False, "used_file": False})
