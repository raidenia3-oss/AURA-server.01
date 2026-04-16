import os
import requests
import personality
from search import smart_search
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from upstash_vector import Index
from automation import GameAgent

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
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")

# --- MODELOS ---
def call_llm(messages: list) -> str:
    if OR_KEY:
        try:
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
            if 'choices' in ans_raw:
                return ans_raw['choices'][0]['message']['content']
        except:
            pass
    if GOOGLE_KEY:
        try:
            google_messages = [
                {"role": m["role"] if m["role"] != "system" else "user",
                 "parts": [{"text": m["content"]}]}
                for m in messages if m["role"] != "system"
            ]
            system_text = next((m["content"] for m in messages if m["role"] == "system"), "")
            res = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemma-3-27b-it:generateContent?key={GOOGLE_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": system_text}]},
                    "contents": google_messages
                },
                timeout=20
            )
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except:
            pass
    return "[ERROR]: Todos los modelos fallaron."

# --- ENDPOINT NOTICIAS (para segundo plano) ---
@app.get("/news")
async def get_news():
    try:
        from search import search_bbc, search_tech_news
        news = search_bbc() + search_tech_news()
        if not news:
            return {"news": []}
        lines = [l.strip() for l in news.strip().split("\n") if l.strip()]
        return {"news": lines[:6]}
    except Exception as e:
        return {"news": [], "error": str(e)}

HTML_CHAT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AURA CORE</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --green: #00ff41;
            --green-dim: #00aa2a;
            --green-dark: #002200;
            --bg: #0a0a0a;
            --bg2: #0f0f0f;
            --border: #1a1a1a;
            --text-dim: #444;
        }
        body { background: var(--bg); color: var(--green); font-family: 'Courier New', monospace; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }

        /* HEADER */
        #header {
            background: var(--bg2);
            border-bottom: 1px solid var(--border);
            padding: 8px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
        }
        #header .title { font-size: 13px; letter-spacing: 4px; color: var(--green); }
        #header .right { display: flex; align-items: center; gap: 15px; }
        #status { font-size: 10px; color: var(--text-dim); letter-spacing: 2px; }
        #status.active { color: var(--green); }
        #status.speaking { color: #00aaff; }
        .dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--text-dim); margin-right: 5px; }
        #status.active .dot { background: var(--green); box-shadow: 0 0 6px var(--green); }
        #status.speaking .dot { background: #00aaff; box-shadow: 0 0 6px #00aaff; }

        /* TICKER noticias */
        #news-ticker {
            background: #050505;
            border-bottom: 1px solid var(--border);
            padding: 5px 20px;
            font-size: 10px;
            color: var(--text-dim);
            overflow: hidden;
            white-space: nowrap;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        #news-ticker .label { color: var(--green-dim); flex-shrink: 0; letter-spacing: 2px; }
        #ticker-content { display: inline-block; animation: ticker 40s linear infinite; }
        @keyframes ticker { 0% { transform: translateX(100vw); } 100% { transform: translateX(-100%); } }

        /* MAIN LAYOUT */
        #main { display: flex; flex: 1; overflow: hidden; }

        /* SIDEBAR */
        #sidebar {
            width: 200px;
            background: var(--bg2);
            border-right: 1px solid var(--border);
            padding: 15px 10px;
            display: flex;
            flex-direction: column;
            gap: 5px;
            flex-shrink: 0;
            overflow-y: auto;
        }
        .sidebar-title { font-size: 9px; color: var(--text-dim); letter-spacing: 2px; padding: 5px 8px; margin-top: 10px; }
        .sidebar-btn {
            background: none;
            border: 1px solid var(--border);
            color: var(--text-dim);
            padding: 8px 10px;
            text-align: left;
            cursor: pointer;
            font-family: monospace;
            font-size: 11px;
            transition: all 0.2s;
            border-radius: 2px;
        }
        .sidebar-btn:hover { border-color: var(--green-dim); color: var(--green); background: var(--green-dark); }
        .sidebar-btn.active { border-color: var(--green); color: var(--green); background: var(--green-dark); }

        /* CHAT */
        #chat-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        #chat { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
        #chat::-webkit-scrollbar { width: 4px; }
        #chat::-webkit-scrollbar-track { background: var(--bg); }
        #chat::-webkit-scrollbar-thumb { background: var(--border); }

        /* MENSAJES */
        .msg {
            max-width: 80%;
            padding: 12px 15px;
            border-radius: 2px;
            font-size: 12px;
            line-height: 1.6;
            border: 1px solid var(--border);
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
        .msg.user {
            align-self: flex-end;
            background: var(--green-dark);
            border-color: var(--green-dim);
        }
        .msg.aura {
            align-self: flex-start;
            background: var(--bg2);
            border-color: var(--border);
        }
        .msg.aura:hover { border-color: var(--green-dim); }
        .msg.system {
            align-self: center;
            background: none;
            border-color: var(--border);
            font-size: 10px;
            color: var(--text-dim);
            max-width: 100%;
            text-align: center;
            padding: 5px 15px;
        }
        .msg-header { font-size: 10px; color: var(--green-dim); margin-bottom: 6px; letter-spacing: 1px; }
        .msg-header .tags { display: inline-flex; gap: 5px; margin-left: 8px; }
        .tag { font-size: 9px; padding: 1px 5px; border-radius: 2px; }
        .tag.web { background: #001133; color: #4488ff; border: 1px solid #003366; }
        .tag.file { background: #1a0a00; color: #ff8844; border: 1px solid #663300; }
        .tag.mem { background: #0a0a1a; color: #8844ff; border: 1px solid #330066; }
        .msg-body { white-space: pre-wrap; }

        /* TYPING INDICATOR */
        #typing {
            display: none;
            align-self: flex-start;
            padding: 10px 15px;
            background: var(--bg2);
            border: 1px solid var(--border);
            border-radius: 2px;
            font-size: 11px;
            color: var(--text-dim);
        }
        #typing.show { display: block; }
        .blink { animation: blink 1s infinite; }
        @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

        /* INPUT AREA */
        #input-area {
            background: var(--bg2);
            border-top: 1px solid var(--border);
            padding: 12px 20px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            flex-shrink: 0;
        }
        #toolbar { display: flex; gap: 8px; align-items: center; }
        #file-name { font-size: 10px; color: var(--text-dim); flex: 1; }
        .tool-btn {
            background: none;
            border: 1px solid var(--border);
            color: var(--text-dim);
            padding: 5px 10px;
            cursor: pointer;
            font-family: monospace;
            font-size: 10px;
            transition: all 0.2s;
        }
        .tool-btn:hover { border-color: var(--green-dim); color: var(--green); }
        .tool-btn.active { border-color: #ff4444; color: #ff4444; background: #110000; }
        #input-row { display: flex; gap: 8px; }
        #msgInput {
            flex: 1;
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--green);
            padding: 10px 15px;
            outline: none;
            font-family: monospace;
            font-size: 12px;
            transition: border-color 0.2s;
        }
        #msgInput:focus { border-color: var(--green-dim); }
        #msgInput::placeholder { color: var(--text-dim); }
        #sendBtn {
            background: var(--green);
            border: none;
            color: #000;
            padding: 10px 20px;
            cursor: pointer;
            font-family: monospace;
            font-weight: bold;
            font-size: 12px;
            letter-spacing: 1px;
            transition: background 0.2s;
        }
        #sendBtn:hover { background: #00cc33; }
    </style>
</head>
<body>
    <div id="header">
        <div class="title">◈ AURA SYSTEM v3.5</div>
        <div class="right">
            <div id="status"><span class="dot"></span>STANDBY</div>
        </div>
    </div>

    <div id="news-ticker">
        <span class="label">◈ LIVE</span>
        <span id="ticker-content">Cargando noticias en tiempo real...</span>
    </div>

    <div id="main">
        <div id="sidebar">
            <div class="sidebar-title">◈ COMANDOS</div>
            <button class="sidebar-btn" onclick="quickCmd('busca: noticias mundiales hoy')">📡 Noticias</button>
            <button class="sidebar-btn" onclick="quickCmd('busca: últimas noticias tecnología')">💻 Tech</button>
            <button class="sidebar-btn" onclick="quickCmd('busca: precio GPU Nvidia hoy')">🔧 Hardware</button>
            <button class="sidebar-btn" onclick="quickCmd('qué es ')">📖 Wikipedia</button>

            <div class="sidebar-title">◈ SISTEMA</div>
            <button class="sidebar-btn" id="notifBtn" onclick="toggleNotifications()">🔔 Alertas OFF</button>
            <button class="sidebar-btn" onclick="clearChat()">🗑 Limpiar</button>
            <button class="sidebar-btn" onclick="document.getElementById('fileInput').click()">📎 Archivo</button>
            <input type="file" id="fileInput" accept=".cpp,.c,.py,.txt,.js,.ts,.md,.json" style="display:none" onchange="handleFile()">

            <div class="sidebar-title">◈ ESTADO</div>
            <div style="font-size:10px; color: #333; padding: 5px 8px;" id="mem-status">Memoria: --</div>
            <div style="font-size:10px; color: #333; padding: 5px 8px;" id="search-status">Búsqueda: activa</div>
        </div>

        <div id="chat-area">
            <div id="chat">
                <div class="msg system">◈ AURA v3.5 — Motor dual activo — Búsqueda en tiempo real activada</div>
            </div>
            <div id="typing">AURA procesando<span class="blink">▋</span></div>

            <div id="input-area">
                <div id="toolbar">
                    <span id="file-name">Sin archivo adjunto</span>
                    <button class="tool-btn" id="clearFileBtn" onclick="clearFile()" style="display:none; color:#ff4444;">✕ Quitar</button>
                    <button class="tool-btn" id="voiceBtn" onclick="toggleVoice()">🎤 VOZ</button>
                </div>
                <div id="input-row">
                    <input type="text" id="msgInput" placeholder="Escribe una orden... (usa 'busca:' para forzar búsqueda)" onkeypress="if(event.key==='Enter') send()">
                    <button id="sendBtn" onclick="send()">EJECUTAR</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('msgInput');
        const status = document.getElementById('status');
        const typing = document.getElementById('typing');
        let fileContent = null, fileName = null, isListening = false, recognition = null;
        let notificationsOn = false, newsInterval = null;

        // --- NOTICIAS TICKER ---
        async function loadTicker() {
            try {
                const res = await fetch('/news');
                const data = await res.json();
                if (data.news && data.news.length > 0) {
                    document.getElementById('ticker-content').textContent = data.news.join('  ◈  ');
                    document.getElementById('mem-status').style.color = '#00aa2a';
                }
            } catch(e) {}
        }
        loadTicker();
        setInterval(loadTicker, 5 * 60 * 1000); // actualizar cada 5 min

        // --- NOTIFICACIONES EN SEGUNDO PLANO ---
        async function toggleNotifications() {
            if (!notificationsOn) {
                const perm = await Notification.requestPermission();
                if (perm !== 'granted') { addMsg('system', 'Permiso de notificaciones denegado.'); return; }
                notificationsOn = true;
                document.getElementById('notifBtn').textContent = '🔔 Alertas ON';
                document.getElementById('notifBtn').classList.add('active');
                newsInterval = setInterval(checkNews, 10 * 60 * 1000); // cada 10 min
                addMsg('system', 'Alertas de noticias activadas. AURA te notificará en segundo plano.');
            } else {
                notificationsOn = false;
                document.getElementById('notifBtn').textContent = '🔔 Alertas OFF';
                document.getElementById('notifBtn').classList.remove('active');
                clearInterval(newsInterval);
                addMsg('system', 'Alertas desactivadas.');
            }
        }

        async function checkNews() {
            try {
                const res = await fetch('/news');
                const data = await res.json();
                if (data.news && data.news.length > 0) {
                    const top = data.news[0].replace(/\[.*?\]/g, '').trim();
                    new Notification('AURA — Noticia destacada', {
                        body: top,
                        icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">◈</text></svg>'
                    });
                }
            } catch(e) {}
        }

        // --- ARCHIVOS ---
        function handleFile() {
            const file = document.getElementById('fileInput').files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (e) => {
                fileContent = e.target.result;
                fileName = file.name;
                document.getElementById('file-name').textContent = '📄 ' + fileName;
                document.getElementById('clearFileBtn').style.display = 'inline';
                addMsg('system', `Archivo cargado: ${fileName} (${fileContent.length} chars)`);
            };
            reader.readAsText(file);
        }

        function clearFile() {
            fileContent = null; fileName = null;
            document.getElementById('file-name').textContent = 'Sin archivo adjunto';
            document.getElementById('clearFileBtn').style.display = 'none';
            document.getElementById('fileInput').value = '';
        }

        // --- VOZ ---
        function toggleVoice() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                alert('Usa Chrome para voz.'); return;
            }
            if (isListening) { recognition.stop(); return; }
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SR();
            recognition.lang = 'es-ES';
            recognition.onstart = () => {
                isListening = true;
                document.getElementById('voiceBtn').classList.add('active');
                document.getElementById('voiceBtn').textContent = '🔴 ESCUCHANDO';
                setStatus('ESCUCHANDO', 'active');
            };
            recognition.onresult = (e) => { input.value = e.results[0][0].transcript; send(); };
            recognition.onend = () => {
                isListening = false;
                document.getElementById('voiceBtn').classList.remove('active');
                document.getElementById('voiceBtn').textContent = '🎤 VOZ';
                setStatus('STANDBY', '');
            };
            recognition.start();
        }

        function speak(text) {
            if (!('speechSynthesis' in window)) return;
            window.speechSynthesis.cancel();
            const utt = new SpeechSynthesisUtterance(text.replace(/[*#`\[\]]/g, '').substring(0, 300));
            utt.lang = 'es-ES'; utt.rate = 1.1;
            const voices = window.speechSynthesis.getVoices();
            const v = voices.find(v => v.lang.startsWith('es') && (v.name.includes('Paulina') || v.name.includes('Monica') || v.name.includes('Laura')))
                   || voices.find(v => v.lang.startsWith('es'));
            if (v) utt.voice = v;
            utt.onstart = () => setStatus('HABLANDO', 'speaking');
            utt.onend = () => setStatus('STANDBY', '');
            window.speechSynthesis.speak(utt);
        }

        function setStatus(text, cls) {
            status.innerHTML = `<span class="dot"></span>${text}`;
            status.className = cls;
        }

        // --- MENSAJES ---
        function addMsg(type, text, meta={}) {
            const div = document.createElement('div');
            div.className = 'msg ' + type;
            if (type === 'system') {
                div.textContent = text;
            } else {
                let tags = '';
                if (meta.web) tags += '<span class="tag web">🌐 WEB</span>';
                if (meta.file) tags += '<span class="tag file">📄 ARCHIVO</span>';
                if (meta.mem) tags += '<span class="tag mem">🧠 MEMORIA</span>';
                const label = type === 'aura' ? 'AURA' : 'RAIDEN';
                div.innerHTML = `<div class="msg-header">${label}<span class="tags">${tags}</span></div><div class="msg-body">${text.replace(/\n/g,'<br>')}</div>`;
            }
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
            return div;
        }

        function clearChat() {
            chat.innerHTML = '<div class="msg system">◈ Chat limpiado.</div>';
        }

        function quickCmd(cmd) {
            input.value = cmd;
            if (cmd.endsWith(' ')) { input.focus(); }
            else { send(); }
        }

        // --- SEND ---
        async function send() {
            const val = input.value.trim();
            if (!val) return;
            input.value = '';
            addMsg('user', val + (fileName ? ` [📄 ${fileName}]` : ''));
            typing.classList.add('show');
            chat.scrollTop = chat.scrollHeight;
            setStatus('PROCESANDO', 'active');

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
                typing.classList.remove('show');
                addMsg('aura', data.content, {
                    web: data.used_search,
                    file: data.used_file,
                    mem: data.used_memory
                });
                speak(data.content);
            } catch(e) {
                typing.classList.remove('show');
                addMsg('system', 'Error de conexión: ' + e.message);
            }
            setStatus('STANDBY', '');
        }

        window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
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
        game_agent = GameAgent()
        data = await request.json()
        messages = data.get("messages", [])
        file_content = data.get("file_content")
        file_name = data.get("file_name")
        user_query = messages[-1]['content'] if messages else ""

        used_search = False
        used_file = False
        used_memory = False

        # Archivo
        file_ctx = ""
        if file_content:
            used_file = True
            file_ctx = f"\n[Archivo: {file_name}]:\n{file_content[:5000]}"

        # Memoria
        mem_ctx = ""
        if vector_index:
            try:
                result = vector_index.query(data=user_query, top_k=1, include_metadata=True)
                for item in result:
                    mem_ctx = f"\n[Memoria]: {item.metadata.get('res')}"
                    used_memory = True
            except:
                pass

        # Búsqueda automática
        web_ctx = ""
        keywords = [
            "busca:", "buscar", "qué es", "que es", "cómo", "como",
            "precio", "noticia", "noticias", "hoy", "actual", "último",
            "ultimo", "2024", "2025", "2026", "error", "solución",
            "solucion", "tutorial", "github", "cuánto", "cuanto",
            "quién", "quien", "dónde", "donde", "cuándo", "cuando",
            "importante", "reciente", "nuevo", "nueva", "lanzó", "lanzo",
            "mundial", "guerra", "tecnología", "tecnologia", "nvidia",
            "gpu", "cpu", "intel", "amd", "apple", "google", "microsoft"
        ]
        if any(k in user_query.lower() for k in keywords):
            web_ctx = smart_search(user_query.replace("busca:", "").strip())
            if web_ctx:
                used_search = True

        messages.insert(0, {
            "role": "system",
            "content": personality.get_system_prompt(mem_ctx, file_ctx, web_ctx)
        })

        ans = call_llm(messages)

        if vector_index:
            try:
                vector_index.upsert(vectors=[(f"msg_{os.urandom(2).hex()}", user_query, {"res": ans})])
            except:
                pass

        return {"content": ans, "used_search": used_search, "used_file": used_file, "used_memory": used_memory}

    except Exception as e:
        return JSONResponse(status_code=500, content={
            "content": f"Fallo en el Nexo: {str(e)}",
            "used_search": False, "used_file": False, "used_memory": False
        })
# ... (toda tu lógica anterior de búsqueda y archivos)

# --- DETECCIÓN DE COMANDOS DE JUEGO ---
game_ctx = ""
if "rollercoin" in user_query.lower() or "juego" in user_query.lower():
    status = game_agent.get_status()
    game_ctx = f"\n[SISTEMA DE JUEGO]: {status}"

# Actualiza el System Prompt para incluir el contexto de juego
messages.insert(0, {
    "role": "system", 
    "content": personality.get_system_prompt(mem_ctx, file_ctx, web_ctx) + game_ctx
})
