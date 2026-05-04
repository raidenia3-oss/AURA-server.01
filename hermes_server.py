# hermes_server.py
# Un pequeño servidor para exponer a Hermes Agent a través de una API local.
# Ejecutar esto en WSL2/Ubuntu.

from flask import Flask, request, jsonify
import subprocess
import os

# Asegúrate de que el path de Hermes esté en tu entorno
# export PATH="/home/raiden/.local/bin:$PATH"
HERMES_PATH = "/home/raiden/.local/bin/hermes"

app = Flask(__name__)

@app.route('/ask', methods=['POST'])
def ask_hermes():
    """Recibe una pregunta, la pasa a Hermes y devuelve la respuesta."""
    data = request.json
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({"error": "No se proporcionó un prompt"}), 400

    try:
        # Ejecuta Hermes como un proceso de línea de comandos
        # Asegúrate de que el comando y los parámetros sean correctos para tu versión de Hermes
        command = [HERMES_PATH, 'run', '--prompt', prompt, '--model', 'gemini-2.5-flash']
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            response_text = result.stdout.strip()
            return jsonify({"response": response_text})
        else:
            error_text = result.stderr.strip()
            return jsonify({"error": f"Error en Hermes: {error_text}"}), 500

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Hermes tardó demasiado en responder"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ejecuta el servidor en el puerto 5000 de tu WSL2
    # Para exponerlo a Windows, necesitarás reenviar el puerto.
    app.run(host='0.0.0.0', port=5000, debug=True)
