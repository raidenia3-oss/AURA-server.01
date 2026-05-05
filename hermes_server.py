# hermes_server.py
# Un pequeño servidor para exponer a Hermes Agent a través de una API local.
# Ejecutar esto en WSL2/Ubuntu.

from flask import Flask, request, jsonify
import subprocess
import os
import sys

# Configuración de rutas - ajusta según tu instalación
HERMES_PATH = os.environ.get("HERMES_PATH", "/home/raiden/.local/bin/hermes")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

app = Flask(__name__)

def check_ollama():
    """Verifica que Ollama esté corriendo y accesible."""
    try:
        import requests
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

@app.route('/ask', methods=['POST'])
def ask_hermes():
    """Recibe una pregunta, la pasa a Hermes y devuelve la respuesta."""
    data = request.json
    prompt = data.get('prompt', '')

    if not prompt:
        return jsonify({"error": "No se proporcionó un prompt"}), 400

    # Verificar que Ollama esté corriendo
    if not check_ollama():
        return jsonify({"error": "Ollama no está corriendo o no es accesible"}), 503

    try:
        # Ejecuta Hermes como un proceso de línea de comandos
        # Ajusta el comando según tu versión de Hermes
        command = [HERMES_PATH, 'run', '--prompt', prompt, '--model', 'dolphin-llama3:8b']

        # Si Hermes no está disponible, usar Ollama directamente como fallback
        if not os.path.exists(HERMES_PATH):
            app.logger.warning(f"Hermes no encontrado en {HERMES_PATH}, usando Ollama directamente")
            import requests
            ollama_response = requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": "dolphin-llama3:8b", "prompt": prompt, "stream": False},
                timeout=120
            )
            if ollama_response.status_code == 200:
                result_data = ollama_response.json()
                return jsonify({"response": result_data.get("response", "Sin respuesta")})
            else:
                return jsonify({"error": f"Error en Ollama: {ollama_response.text}"}), 500

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(HERMES_PATH) if os.path.exists(HERMES_PATH) else None
        )

        if result.returncode == 0:
            response_text = result.stdout.strip()
            if not response_text:
                response_text = "Hermes respondió pero no hay texto (posible error)"
            return jsonify({"response": response_text})
        else:
            error_text = result.stderr.strip()
            app.logger.error(f"Error en Hermes: {error_text}")
            return jsonify({"error": f"Error en Hermes: {error_text}"}), 500

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Hermes tardó demasiado en responder"}), 504
    except FileNotFoundError:
        return jsonify({"error": f"Hermes no encontrado en {HERMES_PATH}"}), 500
    except Exception as e:
        app.logger.error(f"Error inesperado: {str(e)}")
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de verificación de salud."""
    ollama_ok = check_ollama()
    hermes_exists = os.path.exists(HERMES_PATH)

    return jsonify({
        "status": "healthy" if ollama_ok else "degraded",
        "ollama": "running" if ollama_ok else "not running",
        "hermes_path": HERMES_PATH,
        "hermes_exists": hermes_exists,
        "ollama_host": OLLAMA_HOST
    })

if __name__ == '__main__':
    print("🚀 Iniciando Hermes Server...")
    print(f"📍 Hermes path: {HERMES_PATH}")
    print(f"🔗 Ollama host: {OLLAMA_HOST}")
    print(f"🌐 Puerto: 5000")

    # Verificar estado inicial
    ollama_ok = check_ollama()
    hermes_exists = os.path.exists(HERMES_PATH)

    print(f"📊 Ollama: {'✅ OK' if ollama_ok else '❌ No responde'}")
    print(f"📊 Hermes: {'✅ Encontrado' if hermes_exists else '⚠️ No encontrado (usará Ollama directamente)'}")

    # Ejecuta el servidor
    app.run(host='0.0.0.0', port=5000, debug=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
