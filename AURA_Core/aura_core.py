import time
import os
import json
import requests
import subprocess
import pyautogui

# RUTAS ABSOLUTAS
BASE_DIR = r"C:\Users\User\Downloads\AURA\AURA_Core"
NOTAS_PATH = os.path.join(BASE_DIR, "aura_notas.txt")
RESPUESTAS_PATH = os.path.join(BASE_DIR, "aura_respuestas.txt")
MEMORIA_PATH = os.path.join(BASE_DIR, "aura_memoria.json")

def inicializar_todo():
    """Crea la memoria desde cero si falla o no existe"""
    datos_base = {"usuario": "User", "recuerdos_recientes": [], "comandos_exitosos": 0}
    try:
        if not os.path.exists(MEMORIA_PATH):
            with open(MEMORIA_PATH, "w", encoding="utf-8") as f:
                json.dump(datos_base, f, indent=4)
        else:
            # Verificar si la memoria tiene la estructura correcta
            with open(MEMORIA_PATH, "r", encoding="utf-8") as f:
                temp = json.load(f)
                if "recuerdos_recientes" not in temp:
                    raise ValueError("Memoria corrupta")
    except:
        with open(MEMORIA_PATH, "w", encoding="utf-8") as f:
            json.dump(datos_base, f, indent=4)
        print("🧹 Memoria reseteada para evitar errores.")

def ejecutar_en_pc(comando_ia):
    comando_ia = comando_ia.upper()
    try:
        if "CAPTURA" in comando_ia or "FOTO" in comando_ia:
            ruta_foto = os.path.join(BASE_DIR, "captura_aura.png")
            pyautogui.screenshot(ruta_foto)
            return f"Captura guardada en {ruta_foto}"
        
        if "EJECUTAR:" in comando_ia:
            app = comando_ia.split("EJECUTAR:")[1].strip().lower()
            subprocess.Popen(f"start {app}", shell=True)
            return f"Ejecutado: {app}"
    except Exception as e:
        return f"Error de acción: {e}"
    return None

def cargar_skills():
    """Carga todas las instrucciones de la carpeta .skills para el contexto de la IA"""
    skills_content = ""
    skills_dir = os.path.join(BASE_DIR, ".skills")
    if os.path.exists(skills_dir):
        for file in os.listdir(skills_dir):
            if file.endswith(".md"):
                with open(os.path.join(skills_dir, file), "r", encoding="utf-8") as f:
                    skills_content += f"\n--- SKILL: {file} ---\n{f.read()}\n"
    return skills_content

def procesar_con_ia(mensaje):
    try:
        with open(MEMORIA_PATH, "r", encoding="utf-8") as f:
            memoria = json.load(f)
        
        url = "http://localhost:11434/api/generate"
        
        # Cargar skills dinámicamente para el contexto
        skills_context = cargar_skills()
        contexto_base = "Eres Aura, un agente de Windows. Si te piden una foto responde 'EJECUTAR: CAPTURA'. Si te piden una app responde 'EJECUTAR: nombre'."
        contexto_completo = f"{contexto_base}\n\nSigue estrictamente estas reglas y habilidades:\n{skills_context}"
        
        payload = {
            "model": "deepseek-coder:6.7b",
            "prompt": f"{contexto_completo}\nUsuario: {mensaje}",
            "stream": False
        }

        r = requests.post(url, json=payload, timeout=15)
        respuesta = r.json().get('response', '')
        
        accion = ejecutar_en_pc(respuesta)
        final_msg = f"AURA: {accion if accion else respuesta}"

        # Guardar en txt
        with open(RESPUESTAS_PATH, "a", encoding="utf-8") as f:
            f.write(f"TÚ: {mensaje}\n{final_msg}\n---\n")
        print(f"✅ {final_msg}")

    except requests.exceptions.ConnectionError:
        print("⚠️ ERROR: Ollama no está abierto. Ábrelo ahora.")
    except Exception as e:
        print(f"⚠️ Error inesperado: {e}")

if __name__ == "__main__":
    inicializar_todo()
    print("🚀 Aura Agente (Paso 1) LISTO.")
    
    while True:
        if os.path.exists(NOTAS_PATH):
            with open(NOTAS_PATH, "r+", encoding="utf-8") as f:
                orden = f.read().strip()
                if orden:
                    print(f"📩 Leyendo: {orden}")
                    procesar_con_ia(orden)
                    f.truncate(0)
        time.sleep(2)