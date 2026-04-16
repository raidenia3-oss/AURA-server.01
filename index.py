import requests
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

# --- CONFIGURACIÓN DE CONEXIONES ---
OR_KEY = os.environ.get("OPENROUTER_API_KEY")
GROQ_KEY = os.environ.get("GROQ_API_KEY")
W_PHONE = os.environ.get("WHATSAPP_PHONE")
W_KEY = os.environ.get("WHATSAPP_API_KEY")

# --- FUNCIONES DE INVESTIGACIÓN Y MULTIMEDIA ---

def enviar_alerta_whatsapp(mensaje):
    """Envía notificaciones push a tu celular"""
    if W_PHONE and W_KEY:
        url = f"https://api.callmebot.com/whatsapp.php?phone={W_PHONE}&text={mensaje}&apikey={W_KEY}"
        try: requests.get(url, timeout=5)
        except: pass

def investigar_en_red(tema):
    """Acceso a Wikipedia y fuentes globales en tiempo real"""
    try:
        url = f"https://api.duckduckgo.com/?q={tema}&format=json&no_html=1"
        res = requests.get(url, timeout=5).json()
        return res.get('AbstractText', "Buscando detalles técnicos adicionales...")
    except:
        return "Error al conectar con la red de datos externa."

def crear_video_ia(prompt_usuario):
    """Protocolo base para generación de video"""
    # Aquí se conectará con modelos como Sora o Runway en el futuro
    return "Protocolo de generación de video iniciado para: " + prompt_usuario

def analizar_video_con_investigacion(url_video):
    """AURA analiza visualmente y busca contexto técnico"""
    info_video = f"Analizando frames y audio del video en {url_video}..."
    # Simulación de investigación automática basada en temas de tus videos
    busqueda_extra = investigar_en_red("C++ SDL2 game development engines") 
    return f"Resumen visual: {info_video}. Contexto técnico: {busqueda_extra}"

# --- INTERFAZ VISUAL ---
HTML_CHAT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>AURA CORE</title>
    <style>
        :root { --neon: #00ff41; --bg: #0a0a0a; }
        body { background: var(--bg); color: var(--neon); font-family: monospace; margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        #header { padding: 10px; border-bottom: 1px solid #333; text-align: center; font-size: 12px; letter-spacing: 2px; }
        #chat { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; }
        .msg { margin: 8px 0; padding: 12px; border-radius: 5px; max-width: 85%; line-height: 1.4; border-left: 3px solid; }
        .user { align-self: flex-end; background: #002200; border-color: var(--neon); }
        .aura { align-self: flex-start; background: #161616; border-color: #ff0055; }
        #input-area { padding: 10px; background: #000; display: flex; gap: 5px; border-top: 1px solid #222; }
        input { flex: 1; background: #000; border: 1px solid var(--neon); color: var(--neon); padding: 12px; outline: none; }
        button { background: var(--neon); border: none; padding: 10px 15px; font-weight: bold; cursor: pointer; color: #000; }
    </style>
</head>
<body>
    <div id="header">AURA SYSTEM v2.5 [NEURAL LINK ONLINE]</div>
    <div id="chat"></div>
    <div id="input-area">
        <input type="text" id="msgInput" placeholder="Orden para AURA..." onkeypress="if(event.key==='Enter') send()">
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
                const res = await fetch('/api/chat', {
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
def interface():
    return HTML_CHAT

# --- LÓGICA DEL CEREBRO ---

@app.post("/api/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages")
        user_query = messages[-1]['content']
        user_query_low = user_query.lower()

        contexto_investigacion = ""

        # Lógica Automática de AURA
        if "genera un video" in user_query_low:
            contexto_investigacion = crear_video_ia(user_query)
            enviar_alerta_whatsapp(f"AURA: Generando video solicitado: {user_query}")
        
        elif "youtube.com" in user_query_low or "youtu.be" in user_query_low:
            contexto_investigacion = analizar_video_con_investigacion(user_query)
            enviar_alerta_whatsapp("AURA: Análisis profundo de video en curso.")

        elif any(x in user_query_low for x in ["noticias", "que es", "wikipedia", "quien"]):
            contexto_investigacion = investigar_en_red(user_query)

        # Inyectar conocimiento en el Prompt
        system_msg = {
            "role": "system", 
            "content": f"Eres AURA. Datos actuales: {contexto_investigacion}. Eres la IA de Raiden, experta en C++, motores de juego y modelos como Gemma 4."
        }
        messages.insert(0, system_msg)

        # Llamada a modelo gratuito
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}"},
            json={"model": "meta-llama/llama-3.1-8b-instruct:free", "messages": messages},
            timeout=30
        )
        
        respuesta = res.json()['choices'][0]['message']['content']
        return {"content": respuesta}

    except Exception as e:
        return JSONResponse(status_code=500, content={"content": f"Error en el nexo: {str(e)}"})
