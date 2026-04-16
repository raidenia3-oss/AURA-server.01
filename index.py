import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from upstash_vector import Index
import personality  # <--- IMPORTANTE: Conecta la personalidad

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

# (Aquí va todo tu HTML_CHAT igual que antes...)

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        messages = data.get("messages", [])
        user_query = messages[-1]['content'] if messages else ""

        ctx = ""
        if vector_index:
            try:
                search = vector_index.query(data=user_query, top_k=2, include_metadata=True)
                for item in search:
                    ctx += f"\\n[Memoria: {item.metadata.get('res')}]"
            except: pass

        # LLAMADA A LA PERSONALIDAD EXTERNA
        sys_msg = {
            "role": "system", 
            "content": personality.get_system_prompt(ctx)
        }
        messages.insert(0, sys_msg)

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OR_KEY}"},
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
        return JSONResponse(status_code=500, content={"content": f"Fallo en el núcleo: {str(e)}"})
