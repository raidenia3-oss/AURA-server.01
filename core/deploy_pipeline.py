#!/usr/bin/env python3
"""
AURA DEPLOY PIPELINE — Compilar → Verificar ADB → Instalar → Lanzar
Inspirado en LocalSend/Syncthing: despliegue autónomo post-compilación.

Uso:
  python core/deploy_pipeline.py          # Compilar + Instalar + Lanzar
  python core/deploy_pipeline.py --no-build  # Solo instalar APK existente
  python core/deploy_pipeline.py --force  # Forzar reinstalación (borrar primero)
"""

import subprocess
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# --- Configuración ---
ADB_PATH = r"C:\Users\User\AppData\Local\Android\Sdk\platform-tools\adb.exe"
PROJECT_DIR = Path(__file__).resolve().parent.parent / "AME_ECOSYSTEM" / "ame_app_android"
GRADLEW_BAT = PROJECT_DIR / "gradlew.bat"
APK_OUTPUT = PROJECT_DIR / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
JAVA_HOME = r"C:\Program Files\Java\jdk-11.0.22+7"

# Package name de la app
APP_PACKAGE = "com.ame.ecosystem"
APP_MAIN_ACTIVITY = "com.ame.ecosystem/.MainActivity"


def run_cmd(cmd, cwd=None, timeout=300):
    """Ejecuta un comando y retorna (output, returncode)."""
    try:
        env = os.environ.copy()
        env["JAVA_HOME"] = JAVA_HOME
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", -1
    except Exception as e:
        return f"ERROR: {e}", -1


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERR": "❌"}.get(level, "  ")
    print(f"[{ts}] {icon} {msg}")


def check_adb():
    """Verifica si ADB está disponible y hay dispositivos conectados."""
    output, code = run_cmd([ADB_PATH, "devices"])
    if code != 0:
        log("ADB no encontrado", "ERR")
        return False, []
    lines = [l for l in output.strip().split("\n") if "device" in l and "List" not in l]
    if not lines:
        log("No hay dispositivos Android conectados", "WARN")
        return False, []
    log(f"Dispositivos ADB: {len(lines)}", "OK")
    for l in lines:
        log(f"  → {l.strip()}")
    return True, lines


def build_apk():
    """Compila el APK con Gradle."""
    log("Iniciando compilación Gradle...")
    cmd = [str(GRADLEW_BAT), "assembleDebug"]
    output, code = run_cmd(cmd, cwd=str(PROJECT_DIR), timeout=600)

    if code == 0 and APK_OUTPUT.exists():
        size_mb = APK_OUTPUT.stat().st_size / (1024 * 1024)
        log(f"APK compilado exitosamente ({size_mb:.1f} MB)", "OK")
        return True
    else:
        log(f"Error en compilación (code={code})", "ERR")
        if output:
            for line in output.strip().split("\n")[-10:]:
                log(f"  {line}")
        return False


def clear_app_cache():
    """Borra la caché previa de la app en el dispositivo."""
    log("Limpiando caché previa...")
    run_cmd([ADB_PATH, "shell", "pm", "clear", APP_PACKAGE], timeout=30)
    log("Caché limpiada", "OK")


def install_apk(force=False):
    """Instala el APK en el dispositivo."""
    if not APK_OUTPUT.exists():
        log(f"APK no encontrado: {APK_OUTPUT}", "ERR")
        return False

    if force:
        clear_app_cache()

    log("Instalando APK...")
    cmd = [ADB_PATH, "install"]
    if force:
        cmd.append("-r")
    cmd.extend(["-r", "-d", str(APK_OUTPUT)])

    output, code = run_cmd(cmd, timeout=120)
    if code == 0 and "Success" in output:
        log("APK instalado correctamente", "OK")
        return True
    else:
        log(f"Error al instalar APK: {output}", "ERR")
        return False


def launch_app():
    """Lanza la app principal en el dispositivo."""
    log("Lanzando app AME...")
    cmd = [
        ADB_PATH,
        "shell",
        "am",
        "start",
        "-n",
        APP_MAIN_ACTIVITY,
        "-a",
        "android.intent.action.MAIN",
        "-c",
        "android.intent.category.LAUNCHER",
    ]
    output, code = run_cmd(cmd, timeout=30)
    if code == 0:
        log("App lanzada correctamente", "OK")
        return True
    else:
        log(f"Error al lanzar app: {output}", "ERR")
        return False


def uninstall_app():
    """Desinstala la app completamente."""
    log("Desinstalando app...")
    run_cmd([ADB_PATH, "shell", "pm", "uninstall", APP_PACKAGE], timeout=30)
    log("App desinstalada", "OK")


def get_screenshot():
    """Captura screenshot del dispositivo para verificación."""
    log("Capturando screenshot...")
    remote_path = "/sdcard/aura_deploy_check.png"
    local_path = Path(__file__).parent / "aura_deploy_check.png"

    run_cmd([ADB_PATH, "shell", "screencap", "-p", remote_path], timeout=15)
    run_cmd([ADB_PATH, "pull", remote_path, str(local_path)], timeout=15)

    if local_path.exists():
        log(f"Screenshot guardado: {local_path}", "OK")
        return str(local_path)
    log("No se pudo capturar screenshot", "WARN")
    return None


def deploy_full(force=False):
    """Pipeline completo: Build → Install → Launch."""
    log("=" * 50)
    log("AURA DEPLOY PIPELINE v1.0")
    log("=" * 50)

    # 1. Verificar ADB
    adb_ok, devices = check_adb()
    if not adb_ok:
        log("No hay dispositivos conectados. Abortando.", "ERR")
        return False

    # 2. Compilar APK
    if not build_apk():
        log("Compilación fallida. Abortando.", "ERR")
        return False

    # 3. Instalar APK
    if not install_apk(force=force):
        log("Instalación fallida. Abortando.", "ERR")
        return False

    # 4. Lanzar app
    if not launch_app():
        log("No se pudo lanzar la app", "WARN")

    # 5. Screenshot de verificación
    get_screenshot()

    log("=" * 50)
    log("DESPLEGUE COMPLETADO", "OK")
    log("=" * 50)
    return True


def deploy_only(force=False):
    """Solo instalar APK existente sin compilar."""
    log("=" * 50)
    log("AURA DEPLOY — Solo Instalación")
    log("=" * 50)

    adb_ok, devices = check_adb()
    if not adb_ok:
        return False

    if not install_apk(force=force):
        return False

    launch_app()
    get_screenshot()
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AURA Deploy Pipeline")
    parser.add_argument("--no-build", action="store_true", help="Solo instalar APK existente")
    parser.add_argument("--force", action="store_true", help="Forzar reinstalación")
    args = parser.parse_args()

    if args.no_build:
        success = deploy_only(force=args.force)
    else:
        success = deploy_full(force=args.force)

    sys.exit(0 if success else 1)
