"""
Búsqueda web ligera para AURA ("busca en internet: <tema>").

Usa la API de Búsqueda de Gemini (Google) si ``GEMINI_API_KEY`` está
presente; si no, hace un fallback a un scrape del sitio de búsqueda
de Google vía httpx. Devuelve una lista de URLs candidatas para que
``browser.fetch_clean_text`` las raspe.
"""

from __future__ import annotations

import os
import re
from typing import List

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


def _gemini_search(query: str, num_results: int = 3) -> List[str]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return []
    base = os.getenv(
        "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
    )
    url = f"{base}/models/gemini-2.0-flash:generateContent?key={key}"
    prompt = (
        f"Devuelve {num_results} URLs reales y funcionando sobre el "
        f"tema '{query}'. Responde SOLO con una lista numerada de URLs, "
        f"una por línea, sin texto extra."
    )
    try:
        import requests

        resp = requests.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        return re.findall(r"https?://[^\s<>\"'\]\)]+", text)[:num_results]
    except Exception as exc:  # pragma: no cover
        print(f"[web_search] Gemini falló: {exc}")
        return []


def _scrape_google(query: str, num_results: int = 3) -> List[str]:
    if httpx is None:
        return []
    try:
        with httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (AURA-Bot/1.0)"},
        ) as client:
            resp = client.get("https://www.google.com/search", params={"q": query, "num": num_results})
            resp.raise_for_status()
            html = resp.text
        # Extraer hrefs de resultados (limpiando el redirect de Google).
        links = re.findall(r'/url\?q=(https?[^&"\'<>]+)', html)
        clean: List[str] = []
        for lnk in links:
            lnk = re.sub(r"%25", "%", lnk)  # doble encode ocasional
            if lnk.startswith("http") and "google" not in lnk:
                clean.append(lnk)
        # Fallback: cualquier URL suelta.
        if not clean:
            clean = re.findall(r"https?://[^\s<>\"'\]\)]+", html)
        seen = dict.fromkeys(clean)
        return [u for u in seen if "google" not in u][:num_results]
    except Exception as exc:  # pragma: no cover
        print(f"[web_search] scrape falló: {exc}")
        return []


def search(query: str, num_results: int = 3) -> List[str]:
    """Devuelve hasta ``num_results`` URLs sobre ``query``."""
    urls = _gemini_search(query, num_results)
    if urls:
        return urls
    return _scrape_google(query, num_results)
