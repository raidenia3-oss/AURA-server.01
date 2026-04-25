import os
import json
import time
import random
import requests
from playwright.sync_api import sync_playwright

REFRESH_TOKEN = os.environ.get("RC_REFRESH_TOKEN", "").strip()
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")
WHATSAPP_APIKEY = os.environ.get("WHATSAPP_APIKEY", "")

BASE_URL = "https://rollercoin.com"
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://rollercoin.com",
    "Referer": "https://rollercoin.com/game",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def send_whatsapp(msg):
    if not WHATSAPP_NUMBER or not WHATSAPP_APIKEY:
        return
    try:
        requests.get(
            "https://api.callmebot.com/whatsapp.php",
            params={"phone": WHATSAPP_NUMBER, "text": msg, "apikey": WHATSAPP_APIKEY},
            timeout=10
        )
    except:
        pass

def run_bot():
    report = ["◈ AURA — REPORTE ROLLERCOIN"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        # Ir a RollerCoin primero para que el dominio esté activo
        page.goto("https://rollercoin.com/", timeout=30000)
        page.wait_for_timeout(2000)

        # Inyectar token JWT en localStorage
        page.evaluate(f'''
            localStorage.setItem('token', '{REFRESH_TOKEN}');
            localStorage.setItem('refreshToken', '{REFRESH_TOKEN}');
        ''')

        # Recargar con el token inyectado
        page.goto("https://rollercoin.com/dashboard", timeout=30000)
        page.wait_for_timeout(4000)

        current_url = page.url
        print(f"URL: {current_url}")

        if "dashboard" not in current_url:
            report.append(f"❌ Sesión falló (URL: {current_url})")
            send_whatsapp("\n".join(report))
            browser.close()
            return

        report.append("✅ Sesión activa")

        # Obtener balance
        try:
            balance = page.locator("[class*='balance'], [class*='hash']").first.inner_text()
            report.append(f"⚡ Poder: {balance}")
        except:
            pass

        # Recompensa diaria
        try:
            page.goto("https://rollercoin.com/dashboard", timeout=30000)
            page.wait_for_timeout(3000)
            claim = page.locator("text=Claim, text=CLAIM").first
            if claim.is_visible():
                claim.click()
                page.wait_for_timeout(2000)
                report.append("🎁 Recompensa diaria reclamada")
            else:
                report.append("⏳ Recompensa ya reclamada")
        except:
            report.append("⏳ Sin recompensa disponible")

        # Ir a juegos
        try:
            page.goto("https://rollercoin.com/game/choose_game", timeout=30000)
            page.wait_for_timeout(4000)

            games_played = 0
            # Buscar botones START
            start_buttons = page.locator("button:has-text('START'), a:has-text('START')").all()
            print(f"Botones START encontrados: {len(start_buttons)}")

            for i, btn in enumerate(start_buttons[:3]):
                try:
                    print(f"Jugando juego {i+1}...")
                    btn.click()
                    page.wait_for_timeout(3000)

                    # Esperar que cargue el juego
                    page.wait_for_url("**/play_game**", timeout=10000)
                    page.wait_for_timeout(2000)

                    # Buscar botón START dentro del juego
                    inner_start = page.locator("text=START, text=Start").first
                    if inner_start.is_visible():
                        inner_start.click()
                        print(f"Juego {i+1} iniciado, esperando...")
                        # Esperar que termine (máximo 60 segundos)
                        page.wait_for_timeout(60000)
                        games_played += 1

                    # Volver a elegir juego
                    page.goto("https://rollercoin.com/game/choose_game", timeout=30000)
                    page.wait_for_timeout(3000)

                except Exception as e:
                    print(f"Error juego {i+1}: {e}")
                    page.goto("https://rollercoin.com/game/choose_game", timeout=30000)
                    page.wait_for_timeout(2000)
                    continue

            report.append(f"🎮 Juegos completados: {games_played}")

        except Exception as e:
            report.append(f"⚠️ Error juegos: {str(e)[:80]}")

        # Screenshot final
        page.screenshot(path="final.png")
        browser.close()

    report.append("— AURA Bot v3.0")
    final = "\n".join(report)
    print(final)
    send_whatsapp(final)

if __name__ == "__main__":
    run_bot()