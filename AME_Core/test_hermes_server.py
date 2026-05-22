#!/usr/bin/env python3
"""
Script de prueba para hermes_server.py
Ejecutar desde WSL2: python test_hermes_server.py
"""

import requests
import time
import sys

def test_health():
    """Prueba el endpoint de salud."""
    print("🔍 Probando endpoint /health...")
    try:
        response = requests.get("http://127.0.0.1:5000/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check exitoso:")
            print(f"   Status: {data.get('status')}")
            print(f"   Ollama: {data.get('ollama')}")
            print(f"   Hermes: {'Encontrado' if data.get('hermes_exists') else 'No encontrado'}")
            return True
        else:
            print(f"❌ Health check falló: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error en health check: {e}")
        return False

def test_ask():
    """Prueba el endpoint /ask."""
    print("\n🤖 Probando endpoint /ask...")
    try:
        payload = {"prompt": "Di 'Hola desde la prueba' y explica brevemente qué eres."}
        response = requests.post("http://127.0.0.1:5000/ask", json=payload, timeout=60)

        if response.status_code == 200:
            data = response.json()
            if "response" in data:
                print("✅ Respuesta exitosa:")
                print(f"   Respuesta: {data['response'][:200]}...")
                return True
            else:
                print(f"❌ Respuesta sin campo 'response': {data}")
                return False
        else:
            print(f"❌ Error en /ask: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error en /ask: {e}")
        return False

def main():
    print("🚀 Iniciando pruebas de hermes_server.py")
    print("=" * 50)

    # Esperar un poco para que el servidor inicie
    print("⏳ Esperando que el servidor inicie...")
    time.sleep(3)

    # Probar health
    health_ok = test_health()

    # Probar ask solo si health está OK
    if health_ok:
        ask_ok = test_ask()
        if ask_ok:
            print("\n🎉 Todas las pruebas pasaron exitosamente!")
            return 0
        else:
            print("\n⚠️ Health OK pero /ask falló")
            return 1
    else:
        print("\n❌ Health check falló - el servidor no está funcionando correctamente")
        return 1

if __name__ == "__main__":
    sys.exit(main())