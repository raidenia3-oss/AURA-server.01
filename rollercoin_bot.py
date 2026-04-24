import os
import time
import random
import requests

REFRESH_TOKEN = os.environ.get("RC_REFRESH_TOKEN", "")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")
WHATSAPP_APIKEY = os.environ.get("WHATSAPP_APIKEY", "")

BASE_URL = "https://rollercoin.com/api"
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
    try:
        # El refresh token es un JWT, no JSON — usarlo directamente
        res = requests.post(
            f"{BASE_URL}/user/auth/refresh-token",
            json={"refreshToken": REFRESH_TOKEN.strip()},
            headers=HEADERS,
            timeout=10
        )
        print(f"Status: {res.status_code}")
        print(f"Response: {res.text[:200]}")
        data = res.json()
        token = (data.get("token") or 
                 data.get("accessToken") or 
                 data.get("data", {}).get("token") or
                 data.get("jwt"))
        print(f"Token obtenido: {'OK' if token else 'NONE'}")
        return token
    except Exception as e:
        print(f"Error token: {e}")
        return None

def get_user_info(token):
    try:
        res = requests.get(
            f"{BASE_URL}/user/me",
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=10
        )
        return res.json()
    except:
        return {}

def claim_daily(token):
    try:
        res = requests.post(
            f"{BASE_URL}/user/claim-daily-bonus",
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=10
        )
        print(f"Daily: {res.status_code} {res.text[:100]}")
        return res.status_code == 200
    except Exception as e:
        print(f"Error daily: {e}")
        return False

def get_games(token):
    try:
        res = requests.get(
            f"{BASE_URL}/game/user-games",
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=10
        )
        print(f"Games response: {res.text[:300]}")
        return res.json()
    except:
        return {}

def play_game(token, game_id):
    try:
        res = requests.post(
            f"{BASE_URL}/game/start",
            json={"gameId": game_id},
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=10
        )
        print(f"Start {game_id}: {res.text[:100]}")
        time.sleep(5)
        score = random.randint(50, 200)
        res2 = requests.post(
            f"{BASE_URL}/game/finish",
            json={"gameId": game_id, "score": score},
            headers={**HEADERS, "Authorization": f"Bearer {token}"},
            timeout=10
        )
        print(f"Finish {game_id}: {res2.text[:100]}")
        return True
    except Exception as e:
        print(f"Error juego {game_id}: {e}")
        return False

def run_bot():
    report = ["◈ AURA — REPORTE ROLLERCOIN"]

    if not REFRESH_TOKEN:
        report.append("❌ RC_REFRESH_TOKEN no configurado")
        send_whatsapp("\n".join(report))
        return

    token = get_new_token()
    if not token:
        report.append("❌ No se pudo obtener token")
        send_whatsapp("\n".join(report))
        return

    report.append("✅ Sesión activa")

    user = get_user_info(token)
    balance = user.get("balance", "?")
    report.append(f"💰 Balance: {balance} RLT")

    if claim_daily(token):
        report.append("🎁 Recompensa diaria reclamada")
    else:
        report.append("⏳ Recompensa ya reclamada")

    games_data = get_games(token)
    games_played = 0
    games_list = games_data.get("games", games_data.get("data", []))

    if isinstance(games_list, list):
        for game in games_list[:3]:
            game_id = game.get("id") or game.get("gameId") or game.get("_id")
            if game_id and play_game(token, game_id):
                games_played += 1

    report.append(f"🎮 Juegos completados: {games_played}")
    report.append("— AURA Bot v2.0")

    final = "\n".join(report)
    print(final)
    send_whatsapp(final)

if __name__ == "__main__":
    run_bot()
