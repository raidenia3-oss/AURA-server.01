import os
import requests

OR_KEY = os.environ.get("OPENROUTER_API_KEY")
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")

OR_MODELS = [
    "google/gemma-3-27b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/free",
]

def try_groq(messages):
    GROQ_KEY = os.environ.get("GROQ_API_KEY")
    if not GROQ_KEY:
        return None
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={"model": "llama-3.3-70b-versatile", "messages": messages},
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
    if not GOOGLE_KEY:
        return None
    try:
        google_messages = [
            {
                "role": m["role"] if m["role"] != "system" else "user",
                "parts": [{"text": m["content"]}]
            }
            for m in messages if m["role"] != "system"
        ]
        system_text = next(
            (m["content"] for m in messages if m["role"] == "system"), ""
        )
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
    return None

def get_status():
    GROQ_KEY = os.environ.get("GROQ_API_KEY")
    return {
        "GROQ_KEY": "OK" if GROQ_KEY else "MISSING",
        "OR_KEY": "OK" if OR_KEY else "MISSING",
        "GOOGLE_KEY": "OK" if GOOGLE_KEY else "MISSING"
    }

def call_llm(messages: list) -> str:
    result = try_groq(messages)
    if result: return result
    result = try_openrouter(messages)
    if result: return result
    result = try_google(messages)
    if result: return result
    return "[ERROR]: Todos los modelos fallaron."
