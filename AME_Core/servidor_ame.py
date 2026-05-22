"""
AURA Command Center — Flask Server v2
Sirve:
  - Dashboard en '/' (dashboard.html)
  - /api/status → JSON con salud del sistema
  - /api/osint  → POST para ejecutar OSINT (PhoneInfoga / Mr. Holmes)
  - /start/<service>, /stop/<service> para control de bots
"""
import time
import json
import os
import sys
import signal
import subprocess
import threading
import psutil

from flask import Flask, send_from_directory, jsonify, request

# ── Añadir AURA_Core al path para importar OSINTEngine ──
AURA_CORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'AURA_Core')
if AURA_CORE_DIR not in sys.path:
    sys.path.insert(0, AURA_CORE_DIR)

try:
    from osint_engine import OSINTEngine
except ImportError:
    OSINTEngine = None
    print("⚠️  OSINTEngine no disponible (osint_engine.py no encontrado)")

# ──────────────────────── APP ────────────────────────
app = Flask(__name__)
START_TIME = time.time()

# ──── Configuración de Servicios (Bots) ────
SERVICES = {
    "aura_master":    {"script": "aura_core.py",       "process": None, "name": "AURA Master"},
    "crypto_farmer":  {"script": "crypto_farmer_v2.py", "process": None, "name": "Crypto Farmer"},
    "discord_bot":    {"script": "discord_bot.py",      "process": None, "name": "Discord Bot"},
    "escudo_monitor": {"script": "escudo_monitor.py",   "process": None, "name": "Escudo Monitor"},
    "recon_agent":    {"script": "recon.py",            "process": None, "name": "Recon Agent"},
    "osint_engine":   {"script": "osint_engine.py",     "process": None, "name": "OSINT Engine"},
}

# ──── Instancia del Motor OSINT ────
osint_engine = None
if OSINTEngine is not None:
    osint_engine = OSINTEngine()

# ──────────────────── RUTAS ────────────────────

@app.route('/')
def index():
    """Sirve el dashboard AURA."""
    return send_from_directory(os.getcwd(), 'dashboard.html')


@app.route('/api/status')
def api_status():
    """
    JSON con el estado de salud completo del sistema.
    Ejemplo:
    {
      "master_online": true,
      "bots": { "crypto_farmer": true, "discord_bot": false, ... },
      "ram_free_gb": 6.2,
      "ram_total_gb": 16.0,
      "cpu_percent": 23.5,
      "uptime": "0:12:34",
      "system_health": "healthy" | "degraded",
      "active_services": 3,
      "total_services": 6
    }
    """
    # ── RAM ──
    ram = psutil.virtual_memory()
    ram_free_gb  = round(ram.available / (1024**3), 2)
    ram_total_gb = round(ram.total / (1024**3), 2)

    # ── CPU ──
    cpu_percent = psutil.cpu_percent(interval=0.3)

    # ── Uptime ──
    elapsed = time.time() - START_TIME
    hours   = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)
    uptime_str = f"{hours}:{minutes:02d}:{seconds:02d}"

    # ── Estado de cada servicio ──
    bots_status = {}
    online_count = 0
    master_online = False
    for key, srv in SERVICES.items():
        is_alive = srv["process"] is not None and srv["process"].poll() is None
        bots_status[key] = is_alive
        if is_alive:
            online_count += 1
            if key == "aura_master":
                master_online = True

    # ── Health check ──
    system_health = "healthy" if master_online else "degraded"

    return jsonify({
        "master_online":  master_online,
        "bots":           bots_status,
        "online_count":   online_count,
        "total_services": len(SERVICES),
        "ram_free_gb":    ram_free_gb,
        "ram_total_gb":   ram_total_gb,
        "cpu_percent":    cpu_percent,
        "uptime":         uptime_str,
        "system_health":  system_health
    })


@app.route('/api/osint', methods=['POST'])
def api_osint():
    """
    Ejecuta una herramienta OSINT (PhoneInfoga o Mr. Holmes).
    Body JSON: { "tool": "phone" | "email", "target": "+34..." }
    """
    if OSINTEngine is None or osint_engine is None:
        return jsonify({"error": "OSINTEngine no disponible. Verifica osint_engine.py en AURA_Core/"}), 500

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "Body JSON requerido"}), 400

    tool   = data.get("tool", "").strip().lower()
    target = data.get("target", "").strip()

    if not tool or tool not in ("phone", "email"):
        return jsonify({"error": "tool debe ser 'phone' o 'email'"}), 400
    if not target:
        return jsonify({"error": "target requerido"}), 400

    try:
        # Ejecutamos síncrono (el dashboard espera resultado completo)
        result = osint_engine.execute(tool, target, sync=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Error ejecutando OSINT: {str(e)}"}), 500


@app.route('/api/osint/result/<task_id>')
def api_osint_result(task_id):
    """Recupera resultado de una tarea OSINT asíncrona (task_id)."""
    if osint_engine is None:
        return jsonify({"error": "OSINTEngine no disponible"}), 500
    result = osint_engine.get_result(task_id)
    return jsonify(result)


@app.route('/status')
def legacy_status():
    """Endpoint legacy para compatibilidad."""
    status_map = {}
    for key, srv in SERVICES.items():
        if srv["process"] and srv["process"].poll() is None:
            status_map[key] = "ONLINE"
        else:
            status_map[key] = "OFFLINE"
    return jsonify(status_map)


@app.route('/start/<service>')
def start_service(service):
    """Inicia un servicio/bot específico."""
    if service not in SERVICES:
        return jsonify({"error": f"Servicio '{service}' no encontrado"}), 404

    srv = SERVICES[service]
    if srv["process"] and srv["process"].poll() is None:
        return jsonify({"message": f"{srv['name']} ya está activo"}), 200

    try:
        # Determinar el directorio base (AME_Core)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, srv["script"])

        cmd = [sys.executable, script_path]
        log_path = os.path.join(script_dir, f"log_{service}.txt")

        with open(log_path, "a") as log_file:
            srv["process"] = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                cwd=script_dir
            )
        return jsonify({"message": f"{srv['name']} iniciado", "service": service})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/stop/<service>')
def stop_service(service):
    """Detiene un servicio/bot específico."""
    if service not in SERVICES:
        return jsonify({"error": f"Servicio '{service}' no encontrado"}), 404

    srv = SERVICES[service]
    if not srv["process"] or srv["process"].poll() is not None:
        return jsonify({"message": f"{srv['name']} no está activo"}), 200

    try:
        # Intentar terminación gradual, luego forzar
        proc = srv["process"]
        if os.name == 'nt':
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()

        # Esperar hasta 3s
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        srv["process"] = None
        return jsonify({"message": f"{srv['name']} detenido", "service": service})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/update_mobile_ip', methods=['POST'])
def update_mobile_ip():
    """Recibe actualización de IP móvil desde el webhook de AURA_Core."""
    data = request.get_json(force=True)
    if not data or 'mobile_ip' not in data:
        return jsonify({"error": "mobile_ip requerido"}), 400
    new_ip = data['mobile_ip']
    # Guardar en archivo auxiliar para persistencia entre reinicios
    ip_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'AURA_Core', 'config.json')
    try:
        if os.path.exists(ip_file):
            with open(ip_file, 'r') as f:
                cfg = json.load(f)
        else:
            cfg = {}
        cfg['mobile_ip'] = new_ip
        cfg['last_seen'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        with open(ip_file, 'w') as f:
            json.dump(cfg, f, indent=2)
        print(f"📱 [AME Server] IP móvil actualizada vía webhook: {new_ip}")
        return jsonify({"status": "ok", "mobile_ip": new_ip})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health')
def health():
    """Healthcheck simple."""
    return jsonify({"status": "alive", "uptime": time.time() - START_TIME})


# ──────────────────────── MAIN ────────────────────────

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 AURA Command Center — Servidor Flask v2")
    print(f"📡 Escuchando en: http://0.0.0.0:5000")
    print(f"📊 Dashboard:    http://localhost:5000/")
    print(f"🔧 API Status:   http://localhost:5000/api/status")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)