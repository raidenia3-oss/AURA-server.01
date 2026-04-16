import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from upstash_vector import Index
from duckduckgo_search import DDGS # Buscador gratuito e ilimitado
import personality

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

# (Interfaz HTML_CHAT se mantiene igual)

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        user_query = messages[-1]['content'] if messages else ""

        # --- FASE 1: CONEXIÓN A INTERNET GRATUITA ---
        resultados_web = ""
        try:
            with DDGS() as ddgs:
                # Busca los 3 mejores resultados de forma gratuita
                busqueda = [r for r in ddgs.text(user_query, max_results=3)]
                for r in busqueda:
                    resultados_web += f"\\nFuente: {r['title']} - Contenido: {r['body']}"
        except Exception as e:
            resultados_web = "No se pudo acceder a la red en este ciclo."

        # Memoria Upstash
        ctx = ""
        if vector_index:
            try:
                search = vector_index.query(data=user_query, top_k=2, include_metadata=True)
                for item in search:
                    ctx += f"\\n[Memoria: {item.metadata.get('res')}]"
            except: pass

        # Inyectamos Personalidad + Info Web
        sys_msg = {
            "role": "system",
            "content": personality.get_system_prompt(ctx, resultados_web)
        }
        messages.insert(0, sys_msg)

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OR_KEY}",
                "HTTP-Referer": "https://aura-server-01.vercel.app"
            },
            json={
                "model": "openrouter/free", 
                "messages": messages
            },
            timeout=20
        )

        ans_raw = res.json()
        ans = ans_raw['choices'][0]['message']['content']

        if vector_index:
            try:
                vector_index.upsert(vectors=[(f"msg_{os.urandom(4).hex()}", user_query, {"res": ans})])
            except: pass

        return {"content": ans}

    except Exception as e:
        return JSONResponse(status_code=500, content={"content": f"[EXCEPCIÓN CRÍTICA]: {str(e)}"})
