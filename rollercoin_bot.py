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

def get_new_token():
    # RollerCoin API real encontrada en el código fuente
    endpoints = [
        "https://rollercoin.com/api/user/token",
        "https://rollercoin.com/api/user/auth/token",
        "https://rollercoin.com/api/auth/token",
    ]
    for url in endpoints:
        try:
            res = requests.post(
                url,
                json={"refreshToken": REFRESH_TOKEN},
                headers=HEADERS,
                timeout=10
            )
            print(f"{url}: {res.status_code} - {res.text[:150]}")
            if res.status_code == 200:
                data = res.json()
                token = (data.get("token") or
                         data.get("accessToken") or
                         data.get("data", {}).get("token"))
                if token:
                    return token
        except Exception as e:
            print(f"Error {url}: {e}")
    return None

def run_bot():
    report = ["◈ AURA — REPORTE ROLLERCOIN"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        page.goto("https://rollercoin.com/", timeout=30000)
        page.wait_for_timeout(2000)

        # Inyectar refreshToken — RollerCoin lo usa para obtener accessToken automáticamente
        page.evaluate(f"""
            localStorage.setItem('refreshToken', '{REFRESH_TOKEN}');
        """)

        page.goto("https://rollercoin.com/dashboard", timeout=30000)
        page.wait_for_timeout(6000)

        current_url = page.url
        print(f"URL: {current_url}")
        page.screenshot(path="final.png")

        if "dashboard" not in current_url:
            report.append(f"❌ Sesión falló (URL: {current_url})")
            send_whatsapp("\n".join(report))
            browser.close()
            return

        report.append("✅ Sesión activa")

        # Recompensa diaria
        try:
            claim = page.locator("text=Claim").first
            if claim.is_visible():
                claim.click()
                page.wait_for_timeout(2000)
                report.append("🎁 Recompensa diaria reclamada")
            else:
                report.append("⏳ Recompensa ya reclamada")
        except:
            report.append("⏳ Sin recompensa")

        # Juegos
        try:
            page.goto("https://rollercoin.com/game/choose_game", timeout=30000)
            page.wait_for_timeout(4000)

            games_played = 0
            start_buttons = page.locator("button:has-text('START')").all()
            print(f"Botones START: {len(start_buttons)}")

            for i, btn in enumerate(start_buttons[:3]):
                try:
                    btn.click()
                    page.wait_for_timeout(3000)
                    page.wait_for_url("**/play_game**", timeout=10000)
                    page.wait_for_timeout(2000)

                    inner_start = page.locator("text=START").first
                    if inner_start.is_visible():
                        inner_start.click()
                        page.wait_for_timeout(60000)
                        games_played += 1

                    page.goto("https://rollercoin.com/game/choose_game", timeout=30000)
                    page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"Error juego {i+1}: {e}")
                    page.goto("https://rollercoin.com/game/choose_game", timeout=30000)
                    page.wait_for_timeout(2000)

            report.append(f"🎮 Juegos completados: {games_played}")
        except Exception as e:
            report.append(f"⚠️ Error juegos: {str(e)[:80]}")

        browser.close()

    report.append("— AURA Bot v3.1")
    final = "\n".join(report)
    print(final)
    send_whatsapp(final)

if __name__ == "__main__":
    run_bot()
