import requests
import json

# Prueba el servidor Hermes local
url = "http://127.0.0.1:5000/ask"
payload = {"prompt": "Di 'Hola desde la prueba' y explica brevemente qué eres."}

print("🔍 Probando servidor Hermes local...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    print("📤 Enviando petición...")
    response = requests.post(url, json=payload, timeout=30)
    print(f"✅ Respuesta recibida!")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Response: {response.text}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ JSON Response: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ Error HTTP: {response.status_code}")

except requests.exceptions.ConnectionError as e:
    print(f"❌ Error de conexión: {e}")
except requests.exceptions.Timeout as e:
    print(f"❌ Timeout: {e}")
except Exception as e:
    print(f"❌ Error general: {e}")
    import traceback
    traceback.print_exc()