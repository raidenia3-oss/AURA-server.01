import os
import json
from playwright.sync_api import sync_playwright

RC_COOKIES = os.environ.get("RC_COOKIES", "")

def load_cookies():
    try:
        cookies_data = json.loads(RC_COOKIES)
        return [{"name": c["name"], "value": c["value"], 
                 "domain": c.get("domain", ".rollercoin.com"),
                 "path": c.get("path", "/"),
                 "httpOnly": c.get("httpOnly", False),
                 "secure": c.get("secure", True)} for c in cookies_data]
    except Exception as e:
        print(f"Error: {e}")
        return []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    context.add_cookies(load_cookies())
    page = context.new_page()
    
    page.goto("https://rollercoin.com/game", timeout=30000)
    page.wait_for_timeout(5000)
    
    print("URL:", page.url)
    print("Titulo:", page.title())
    
    # Imprimir todos los elementos clickeables
    buttons = page.locator("button, a, [onclick]").all()
    print(f"\nBotones encontrados: {len(buttons)}")
    for i, btn in enumerate(buttons[:20]):
        try:
            text = btn.inner_text()
            cls = btn.get_attribute("class") or ""
            href = btn.get_attribute("href") or ""
            if text.strip():
                print(f"  [{i}] texto='{text.strip()[:50]}' class='{cls[:50]}' href='{href[:50]}'")
        except:
            continue
    
    page.screenshot(path="debug.png", full_page=True)
    print("\nScreenshot guardado")
    browser.close()