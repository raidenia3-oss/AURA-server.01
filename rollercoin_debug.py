import os
import json
import requests
from playwright.sync_api import sync_playwright

RC_COOKIES = os.environ.get("RC_COOKIES", "")

def load_cookies():
    try:
        cookies_data = json.loads(RC_COOKIES)
        return [{"name": c["name"], "value": c["value"], "domain": c.get("domain", ".rollercoin.com"), "path": c.get("path", "/"), "httpOnly": c.get("httpOnly", False), "secure": c.get("secure", True)} for c in cookies_data]
    except:
        return []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    context.add_cookies(load_cookies())
    page = context.new_page()
    
    page.goto("https://rollercoin.com/game", timeout=30000)
    page.wait_for_timeout(5000)
    
    # Guardar HTML para analizar
    html = page.content()
    with open("game_page.html", "w") as f:
        f.write(html)
    
    # Captura de pantalla
    page.screenshot(path="game_page.png", full_page=True)
    print("HTML y screenshot guardados")
    print("URL actual:", page.url)
    
    # Buscar elementos de juego
    elements = page.locator("[class*='game'], [class*='Game'], [id*='game']").all()
    print(f"Elementos encontrados: {len(elements)}")
    for i, el in enumerate(elements[:5]):
        print(f"  {i}: {el.get_attribute('class')}")
    
    browser.close()