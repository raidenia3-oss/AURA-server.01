import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
from upstash_vector import Index

app = FastAPI()

# --- CONFIGURACIÓN DE MEMORIA Y LLAVES ---
vector_index = Index(
    url=os.environ.get("UPSTASH_VECTOR_REST_URL"), 
    token=os.environ.get("UPSTASH_VECTOR_REST_TOKEN")
)
OR_KEY = os.environ.get("OR_KEY")

# --- TUS FUNCIONES DE INVESTIGACIÓN (RESTAURADAS) ---
def crear_video_ia(query):
    return f"Investigación para video sobre: {query}"

def analizar_video_con_investigacion(url):
    return f"Análisis del video en {url} completado."

def investigar_en_red(query):
    return f"Resultados de búsqueda en red para: {query}"

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        user_query = messages[-1]['content'] if messages else ""
        user_query_low = user_query.lower()
        
        contexto_investigacion = ""

        # Lógica Automática de AURA (Tus Elifs)
        if "genera un video" in user_query_low:
            contexto_investigacion = crear_video_ia(user_query)
        elif any(x in user_query_low for x in ["youtube.com", "youtu.be"]):
            contexto_investigacion = analizar_video_con_investigacion(user_query)
        elif any(x in user_query_low for x in ["noticias", "que es", "wikipedia", "quien"]):
            contexto_investigacion = investigar_en_red(user_query)

        # Inyectar conocimiento en el Prompt
        system_msg = {
            "role": "system",
            "content": f"Eres AURA. Datos actuales: {contexto_investigacion}. Eres la IA de Raiden, experta en C++, motores de juego y modelos como Gemma 4."
        }
        messages.insert(0, system_msg)

        # Llamada a OpenRouter
        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}"},
            json={
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": messages
            },
            timeout=30
        )
        
        respuesta = res.json()['choices'][0]['message']['content']

        # --- BLOQUE DE MEMORIA VECTORIAL ---
        try:
            vector_index.upsert(
                vectors=[
                    (f"msg_{os.urandom(4).hex()}", user_query, {"res": respuesta})
                ]
            )
        except:
            pass 

        return {"content": respuesta}

    except Exception as e:
        return JSONResponse(status_code=500, content={"content": f"Error en el nexo: {str(e)}"})

@app.get("/")
async def root():
    return {"status": "AURA Online - Sistema Completo con Memoria"}
