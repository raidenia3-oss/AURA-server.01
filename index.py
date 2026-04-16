import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
from upstash_vector import Index

app = FastAPI()

# --- CONFIGURACIÓN DE MEMORIA (UPSTASH) ---
vector_index = Index(
    url=os.environ.get("UPSTASH_VECTOR_REST_URL"), 
    token=os.environ.get("UPSTASH_VECTOR_REST_TOKEN")
)

OR_KEY = os.environ.get("OR_KEY")

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        user_query = messages[-1]['content'] if messages else ""
        
        # Llamada a OpenRouter (Llama 3.1)
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
        except Exception as mem_err:
            print(f"Error de memoria: {mem_err}")
            # Si la memoria falla, el chat sigue funcionando
            pass

        return {"content": respuesta}

    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"content": f"Error en el nexo AURA: {str(e)}"}
        )

@app.get("/")
async def root():
    return {"status": "Servidor AURA Activo - Memoria Conectada"}
