import os
import json
import time
import requests
from playwright.sync_api import sync_playwright

RC_COOKIES = os.environ.get("RC_COOKIES", "")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")
WHATSAPP_APIKEY = os.environ.get("WHATSAPP_APIKEY", "")

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

def load_cookies():
    try:
        cookies_data = json.loads(RC_COOKIES)
        pw_cookies = []
        for c in cookies_data:
            pw_cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".rollercoin.com"),
                "path": c.get("path", "/"),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", True),
            })
        return pw_cookies
    except Exception as e:
        print(f"Error cargando cookies: {e}")
        return []

def run_bot():
    report = []
    report.append("◈ AURA — REPORTE ROLLERCOIN")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        cookies = load_cookies()
        if cookies:
            context.add_cookies(cookies)
            print(f"Cargadas {len(cookies)} cookies")
        else:
            report.append("❌ Error: No se pudieron cargar las cookies")
            send_whatsapp("\n".join(report))
            return

        page = context.new_page()
        page.goto("https://rollercoin.com/", timeout=30000)
        page.wait_for_timeout(3000)

        if "login" in page.url.lower():
            report.append("❌ Sesión expirada — renueva las cookies")
            send_whatsapp("\n".join(report))
            browser.close()
            return

        report.append("✅ Sesión activa")

        # Recompensa diaria
        try:
            page.goto("https://rollercoin.com/dashboard", timeout=30000)
            page.wait_for_timeout(3000)
            daily = page.locator("text=Claim").first
            if daily.is_visible():
                daily.click()
                page.wait_for_timeout(2000)
                report.append("🎁 Recompensa diaria reclamada")
            else:
                report.append("⏳ Recompensa ya reclamada hoy")
        except:
            report.append("⏳ Sin recompensa disponible")

        # Juegos
        try:
            page.goto("https://rollercoin.com/game", timeout=30000)
            page.wait_for_timeout(3000)
            games_played = 0
            games = page.locator(".game-item").all()

            for i, game in enumerate(games[:3]):
                try:
                    game.click()
                    page.wait_for_timeout(5000)
                    play_btn = page.locator("button:has-text('Play')").first
                    if play_btn.is_visible():
                        play_btn.click()
                        page.wait_for_timeout(15000)
                        games_played += 1
                    page.go_back()
                    page.wait_for_timeout(2000)
                except:
                    continue

            report.append(f"🎮 Juegos completados: {games_played}")
        except Exception as e:
            report.append(f"⚠️ Error juegos: {str(e)[:50]}")

        browser.close()

    report.append("— AURA Bot v1.0")
    send_whatsapp("\n".join(report))
    print("\n".join(report))

if __name__ == "__main__":
    run_bot()
