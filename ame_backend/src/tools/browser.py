"""
Herramienta de Navegación Web Autónoma ("garras en la red").

Recibe una URL, la descarga con httpx (timeout corto, headers de bot
éticos) y extrae el texto limpio: quita <script>, <style>, comentarios
HTML y deja solo el contenido legible. Esto alimenta el contexto
enriquecido que se envía a Gemini.
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

# Etiquetas cuyo contenido NO es texto legible.
_SKIP_TAGS = re.compile(
    r"<(script|style|noscript|template|svg|head|meta|link|button|nav|footer|form)[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+")


def _is_safe_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    host = (p.hostname or "").lower()
    if host.endswith("localhost") or host == "127.0.0.1" or host == "0.0.0.0":
        return False
    return bool(p.netloc)


def extract_text(html: str) -> str:
    """Deja solo el texto legible de un documento HTML."""
    if not html:
        return ""
    # Quitar bloques no-texuales primero.
    cleaned = _SKIP_TAGS.sub(" ", html)
    # Quitar comentarios.
    cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.DOTALL)
    # Quitar todas las etiquetas restantes.
    cleaned = _TAG_RE.sub(" ", cleaned)
    # Decodificar entidades básicas.
    cleaned = (
        cleaned.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
    )
    cleaned = _CONTROL_RE.sub(" ", cleaned)
    cleaned = _WS_RE.sub(" ", cleaned).strip()
    return cleaned


def fetch_clean_text(url: str, timeout: float = 15.0, max_chars: int = 6000) -> str:
    """Descara una URL y devuelve su texto limpio (recortado)."""
    if not _is_safe_url(url):
        raise ValueError(f"URL no permitida o insegura: {url}")
    if httpx is None:
        raise RuntimeError("httpx no est instalado")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AURA-Bot/1.0; +https://aura.local)"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }
    with httpx.Client(
        timeout=timeout, follow_redirects=True, headers=headers, verify=True
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "html" not in ctype.lower() and not url.endswith((".html", ".htm", "/")):
            # Solo procesamos HTML; si no, devolvemos un extracto crudo.
            raw = resp.text
        else:
            raw = resp.text
    text = extract_text(raw)
    if len(text) > max_chars:
        text = text[:max_chars] + " …[truncado]"
    return text


async def fetch_clean_text_async(
    url: str, timeout: float = 15.0, max_chars: int = 6000
) -> str:
    """Versión asíncrona (httpx.AsyncClient)."""
    if not _is_safe_url(url):
        raise ValueError(f"URL no permitida o insegura: {url}")
    if httpx is None:
        raise RuntimeError("httpx no est instalado")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AURA-Bot/1.0; +https://aura.local)"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, headers=headers, verify=True
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        raw = resp.text
    text = extract_text(raw)
    if len(text) > max_chars:
        text = text[:max_chars] + " …[truncado]"
    return text


def find_urls(text: str) -> list[str]:
    """Extrae URLs http(s) mencionadas en un mensaje."""
    return re.findall(r"https?://[^\s<>\"'\]\)]+", text)
