#!/usr/bin/env python3
"""
Script de diagnóstico para verificar la configuración de todos los proveedores.
Muestra errores específicos sin exponer las claves en el output.
"""
import os
import sys
import requests
from pathlib import Path

# Cargar variables de entorno desde .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# Configuración de proveedores
PROVIDERS = {
    "openrouter": {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openai/gpt-3.5-turbo",
        "key": "OPENROUTER_API_KEY",
        "format": "openai",
    },
    "groq": {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "mixtral-8x7b-32768",
        "key": "GROQ_API_KEY",
        "format": "openai",
    },
    "gemini": {
        "name": "Google Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
        "model": "gemini-pro",
        "key": "GEMINI_API_KEY",
        "format": "google",
    },
    "mistral": {
        "name": "Mistral AI",
        "url": "https://api.mistral.ai/v1/chat/completions",
        "model": "mistral-7b-instruct-v0.2",
        "key": "MISTRAL_API_KEY",
        "format": "openai",
    },
    "cerebras": {
        "name": "Cerebras",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "model": "cerebras-7b",
        "key": "CEREBRAS_API_KEY",
        "format": "openai",
    },
}

def test_provider(name, config):
    """Prueba un proveedor específico y retorna el resultado."""
    api_key = os.environ.get(config["key"])
    
    if not api_key:
        return {
            "status": "no_key",
            "error": f"Falta la variable {config['key']}",
        }
    
    test_prompt = "Responde solo con 'OK'"
    
    try:
        if config["format"] == "google":
            # Formato Google Gemini
            url = f"{config['url']}?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [{"text": test_prompt}]
                }]
            }
            headers = {"Content-Type": "application/json"}
            
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if res.status_code == 200:
                return {"status": "ok", "latency_ms": res.elapsed.total_seconds() * 1000}
            else:
                error_msg = res.text[:100]
                return {
                    "status": "error",
                    "http_code": res.status_code,
                    "error": error_msg,
                }
        else:
            # Formato OpenAI
            payload = {
                "model": config["model"],
                "messages": [{"role": "user", "content": test_prompt}],
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            
            res = requests.post(config["url"], json=payload, headers=headers, timeout=10)
            
            if res.status_code == 200:
                return {"status": "ok", "latency_ms": res.elapsed.total_seconds() * 1000}
            else:
                error_msg = res.text[:100]
                return {
                    "status": "error",
                    "http_code": res.status_code,
                    "error": error_msg,
                }
    
    except requests.Timeout:
        return {"status": "error", "error": "Timeout - no response from server"}
    except requests.ConnectionError as e:
        return {"status": "error", "error": f"Connection error: {str(e)[:50]}"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {str(e)[:50]}"}

def main():
    print("=" * 80)
    print("🔍 DIAGNÓSTICO DE PROVEEDORES AURA")
    print("=" * 80)
    print()
    
    results = {}
    for provider_id, config in PROVIDERS.items():
        print(f"Probando {config['name']}...", end=" ", flush=True)
        result = test_provider(provider_id, config)
        results[provider_id] = result
        
        if result["status"] == "ok":
            latency = result.get("latency_ms", "?")
            print(f"✓ OK ({latency:.0f}ms)")
        elif result["status"] == "no_key":
            print(f"⚠ Sin clave: {result['error']}")
        else:
            http_code = result.get("http_code", "?")
            error = result.get("error", "desconocido")
            print(f"✗ Error ({http_code}): {error[:40]}")
    
    print()
    print("=" * 80)
    print("📊 RESUMEN")
    print("=" * 80)
    
    working = sum(1 for r in results.values() if r["status"] == "ok")
    no_key = sum(1 for r in results.values() if r["status"] == "no_key")
    failed = sum(1 for r in results.values() if r["status"] == "error")
    
    print(f"  ✓ Funcionando: {working}")
    print(f"  ⚠ Sin clave: {no_key}")
    print(f"  ✗ Con error: {failed}")
    print()
    
    if working > 0:
        print("✅ El sistema de failover está operativo.")
        print("   Si un proveedor falla, AURA alternará al siguiente automáticamente.")
    else:
        print("⚠️ Sin proveedores disponibles. Revisa las claves y la conexión.")
    
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
