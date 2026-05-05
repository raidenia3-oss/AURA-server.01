# hermes_server.py
# Servidor Flask para exponer a Ollama local.

from flask import Flask, request, jsonify
import requests
import os
import sys

app = Flask(__name__)

# URL de tu servidor local de Ollama
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"

# Modelo por defecto (debe estar instalado en Ollama)
DEFAULT_MODEL = "dolphin-llama3:8b" 

@app.route('/ask', methods=['POST'])
def ask_ollama():
    """Recibe una pregunta, la envía a Ollama y devuelve la respuesta."""
    try:
        data = request.json
        prompt = data.get('prompt', '')
        model = data.get('model', DEFAULT_MODEL) # Permite cambiar modelo desde la petición

        if not prompt:
            return jsonify({"response": "Error: No se proporcionó un prompt."}), 400

        print(f"🔍 Hermes recibiendo: \'{prompt}\' (Modelo: {model})")

        # Prepara el payload para la API de Ollama
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,  # No queremos streaming, queremos la respuesta completa
            "options": {
                "temperature": 0.7,
                "num_predict": 256
            }
        }
        
        # Haz la petición POST a Ollama
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status() # Lanza un error si la petición falla (ej: 404, 500)
        
        result = response.json()
        response_text = result.get("response", "Respuesta vacía de Ollama.")
        
        print(f"✅ Hermes responded: {response_text[:50]}...")
        return jsonify({"response": response_text})

    except requests.exceptions.ConnectionError:
        error_msg = "Error: No se pudo conectar a Ollama (11434). Asegúrate de que Ollama esté corriendo."
        print(f"❌ {error_msg}")
        return jsonify({"response": error_msg}), 500
    except Exception as e:
        error_msg = f"Error interno del servidor: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"response": error_msg}), 500

if __name__ == '__main__':
    print("🚀 Iniciando servidor Hermes en puerto 5000...")
    # Inicia el servidor en el puerto 5000, accesible desde la red local
    app.run(host='0.0.0.0', port=5000, debug=False) # debug=False evita reinicios infinitos
