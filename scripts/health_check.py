#!/usr/bin/env python3
"""
health_check.py — Verifica el estado completo de AURA/AME
Incluye: dependencias Python, EventBus, Godot Bridge, Cloudflare Tunnel y AME Config
"""

import os
import sys
import json
import time
import asyncio
import requests
import importlib.util
from pathlib import Path
from datetime import datetime

# Configuración
CHECK_TIMEOUT = 5  # segundos
URLS_FILE = Path(__file__).resolve().parent.parent / "aura_urls.json"
AME_CONFIG_PATH = Path("/sdcard/ame_config.json")  # Ruta en Android
LOCAL_EVENTBUS_URL = "ws://localhost:8765"
LOCAL_GODOT_URL = "ws://localhost:9090"

# Estado global
results = {
    "python_deps": [],
    "eventbus": None,
    "godot_bridge": None,
    "cloudflare_tunnel": None,
    "ame_config": None,
    "ame_connection": None,
    "timestamp": datetime.now().isoformat(),
    "status": "pending"
}

def check_python_deps():
    """Verifica dependencias Python esenciales"""
    required_deps = ["websockets", "asyncio", "json", "sqlite3", "requests"]
    missing = []

    for dep in required_deps:
        try:
            if dep == "asyncio":
                importlib.util.find_spec("asyncio")
            elif dep == "json":
                import json
            elif dep == "sqlite3":
                import sqlite3
            else:
                importlib.util.find_spec(dep)
            results["python_deps"].append({"name": dep, "status": "✅"})
        except:
            results["python_deps"].append({"name": dep, "status": "❌"})
            missing.append(dep)

    if missing:
        print(f"⚠️  Dependencias faltantes: {', '.join(missing)}")
        print("   Instálalas con: pip install websockets requests")
    else:
        print("✅ Todas las dependencias Python están instaladas")

async def check_websocket(url, name):
    """Verifica conexión WebSocket"""
    try:
        import websockets
        async with websockets.connect(url, timeout=CHECK_TIMEOUT) as ws:
            await ws.send(json.dumps({"type": "health_check", "timestamp": datetime.now().isoformat()}))
            response = await asyncio.wait_for(ws.recv(), timeout=CHECK_TIMEOUT)
            results[name] = {"status": "✅", "response": response}
            return True
    except Exception as e:
        results[name] = {"status": "❌", "error": str(e)}
        return False

def check_eventbus():
    """Verifica EventBus local"""
    print(f"🔍 Verificando EventBus en {LOCAL_EVENTBUS_URL}...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(check_websocket(LOCAL_EVENTBUS_URL, "eventbus"))
    loop.close()
    return success

def check_godot_bridge():
    """Verifica Godot Bridge local"""
    print(f"🔍 Verificando Godot Bridge en {LOCAL_GODOT_URL}...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(check_websocket(LOCAL_GODOT_URL, "godot_bridge"))
    loop.close()
    return success

def check_cloudflare_tunnel():
    """Verifica Cloudflare Tunnel"""
    if not URLS_FILE.exists():
        results["cloudflare_tunnel"] = {"status": "❌", "error": "aura_urls.json no encontrado"}
        print("❌ aura_urls.json no encontrado. Ejecuta setup_cloudflare.py primero")
        return False

    try:
        with open(URLS_FILE) as f:
            urls_data = json.load(f)

        tunnel_url = urls_data.get("urls", {}).get("dashboard", "")
        if not tunnel_url:
            results["cloudflare_tunnel"] = {"status": "❌", "error": "URL del túnel no configurada"}
            return False

        print(f"🔍 Verificando Cloudflare Tunnel en {tunnel_url}...")
        try:
            response = requests.get(tunnel_url, timeout=CHECK_TIMEOUT)
            if response.status_code in (200, 101):
                results["cloudflare_tunnel"] = {"status": "✅", "url": tunnel_url}
                return True
            else:
                results["cloudflare_tunnel"] = {"status": "❌", "error": f"HTTP {response.status_code}"}
                return False
        except Exception as e:
            results["cloudflare_tunnel"] = {"status": "❌", "error": str(e)}
            return False

    except Exception as e:
        results["cloudflare_tunnel"] = {"status": "❌", "error": str(e)}
        return False

def check_ame_config():
    """Verifica que ame_config.json exista y sea válido"""
    if not AME_CONFIG_PATH.exists():
        results["ame_config"] = {"status": "❌", "error": "ame_config.json no encontrado en /sdcard/"}
        print("❌ ame_config.json no encontrado en /sdcard/")
        return False

    try:
        with open(AME_CONFIG_PATH) as f:
            config = json.load(f)

        if not config.get("network", {}).get("eventbus_url"):
            results["ame_config"] = {"status": "❌", "error": "Configuración inválida"}
            return False

        results["ame_config"] = {"status": "✅", "path": str(AME_CONFIG_PATH)}
        print("✅ ame_config.json encontrado y válido")
        return True

    except Exception as e:
        results["ame_config"] = {"status": "❌", "error": str(e)}
        return False

def print_report():
    """Imprime el informe de salud del sistema"""
    print("\n" + "="*60)
    print("  🔍 REPORTE DE SALUD DE AURA/AME")
    print("="*60)

    # Dependencias Python
    print("\n🐍 DEPENDENCIAS PYTHON:")
    for dep in results["python_deps"]:
        print(f"   {dep['name']:15s} {dep['status']}")

    # Servicios locales
    print("\n🏠 SERVICIOS LOCALES:")
    for name, res in [("EventBus", results["eventbus"]),
                      ("Godot Bridge", results["godot_bridge"])]:
        status = res["status"] if res else "❌"
        print(f"   {name:15s} {status}")

    # Cloudflare Tunnel
    if results["cloudflare_tunnel"]:
        print(f"\n🌐 CLOUDFLARE TUNNEL:")
        print(f"   URL: {results['cloudflare_tunnel']['url']}")
        print(f"   Estado: {results['cloudflare_tunnel']['status']}")

    # AME Config
    print("\n📱 AME CONFIGURACIÓN:")
    if results["ame_config"]:
        print(f"   Ruta: {results['ame_config']['path']}")
        print(f"   Estado: {results['ame_config']['status']}")

    # Resumen
    print("\n" + "="*60)
    print("  📊 RESUMEN:")
    checks = [
        ("Python Dependencies", all(d["status"] == "✅" for d in results["python_deps"])),
        ("EventBus Local", results["eventbus"] and results["eventbus"]["status"] == "✅"),
        ("Godot Bridge", results["godot_bridge"] and results["godot_bridge"]["status"] == "✅"),
        ("Cloudflare Tunnel", results["cloudflare_tunnel"] and results["cloudflare_tunnel"]["status"] == "✅"),
        ("AME Config", results["ame_config"] and results["ame_config"]["status"] == "✅")
    ]

    ok_count = sum(1 for _, status in checks if status)
    total = len(checks)

    for name, status in checks:
        print(f"   {name:20s} {'✅' if status else '❌'}")

    print(f"\n   ESTADO GENERAL: {ok_count}/{total} OK")

    if ok_count == total:
        print("\n   🎉 ¡Sistema listo para operar!")
    else:
        print("\n   ⚠️  Revisa los ❌ antes de continuar")

    print("="*60)

if __name__ == "__main__":
    print("🔍 Iniciando verificación de salud de AURA/AME...")

    # Verificar dependencias Python
    check_python_deps()

    # Verificar servicios locales
    check_eventbus()
    check_godot_bridge()

    # Verificar Cloudflare Tunnel
    check_cloudflare_tunnel()

    # Verificar AME Config (solo si estamos en Android)
    if sys.platform == "linux" and os.path.exists("/sdcard"):
        check_ame_config()
    else:
        print("⚠️  No se pudo verificar ame_config.json (no en Android)")

    # Imprimir reporte
    print_report()

    # Guardar resultados en JSON
    results_file = Path(__file__).resolve().parent / "health_check_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n📄 Resultados guardados en: {results_file}")