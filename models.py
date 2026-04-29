
import os
import requests

OR_KEY = os.environ.get("OPENROUTER_API_KEY")
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")
NGROK_URL = os.environ.get("NGROK_URL")

OR_MODELS = [
    "google/gemini-flash-1.5:free",
    "mistralai/mistral-7b-instruct:free",
    "openrouter/cinematika-7b:free",
]

def try_ngrok(messages):
    if not NGROK_URL:
        return None
    
    prompt = messages[-1]["content"] if messages else ""

    for intento in range(2):  # Retry if content is empty
        try:
            res = requests.post(
                NGROK_URL + "/api/chat",
                json={
                    "model": "dolphin-llama3:8b",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                },
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "curl/7.68.0",
                    "ngrok-skip-browser-warning": "true"
                },
                timeout=60.0
            )
            if res.status_code == 200:
                data = res.json()
                content = data.get("message", {}).get("content")
                if content:
                    return content
            # If content is empty, retry
        except Exception as e:
            print(f"Ollama error: {e}")
            return None # Allow fallback
    
    return "Ollama cargando modelo, intenta de nuevo en 5 segundos"

def try_groq(messages):
    GROQ_KEY = os.environ.get("GROQ_API_KEY")
    if not GROQ_KEY:
        return None
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": "llama3-70b-8192", "messages": messages},
            timeout=15
        )
        ans = res.json()
        if 'choices' in ans:
            return ans['choices'][0]['message']['content']
    except:
        pass
    return None

def try_openrouter(messages):
    if not OR_KEY:
        return None
    for model in OR_MODELS:
        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OR_KEY}",
                    "HTTP-Referer": "https://aura-server-01.vercel.app",
                    "X-Title": "AURA"
                },
                json={"model": model, "messages": messages},
                timeout=20
            )
            ans = res.json()
            if 'choices' in ans:
                return ans['choices'][0]['message']['content']
        except:
            continue
    return None

def try_google(messages):
    GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")
    if not GOOGLE_KEY:
        return None
    try:
        google_messages = [
            {"role": m["role"] if m["role"] != "system" else "user",
             "parts": [{"text": m["content"]}]}
            for m in messages if m["role"] != "system"
        ]
        system_text = next(
            (m["content"] for m in messages if m["role"] == "system"), ""
        )
        res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_KEY}",
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
    return None

def get_status():
    GROQ_KEY = os.environ.get("GROQ_API_KEY")
    return {
        "GROQ_KEY": "OK" if GROQ_KEY else "MISSING",
        "OR_KEY": "OK" if OR_KEY else "MISSING",
        "GOOGLE_KEY": "OK" if GOOGLE_KEY else "MISSING",
        "NGROK_URL": "OK" if NGROK_URL else "MISSING"
    }

def call_llm(messages: list) -> str:
    result = try_ngrok(messages)
    if result: return result
    result = try_google(messages)
    if result: return result
    result = try_groq(messages)
    if result: return result
    result = try_openrouter(messages)
    if result: return result
    return "[ERROR]: Todos los modelos fallaron."
