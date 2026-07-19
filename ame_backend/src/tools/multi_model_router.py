"""
Enrutador Multi-Modelo ("Modo Libre").

Extiende la lógica de ``ai_engine.AIEngine`` para permitir conexiones a
proveedores abiertos (OpenRouter, DeepInfra) y, cuando el usuario activa el
"Modo Libre", enrutar el tráfico hacia modelos sin restricciones de sistema
usando una API Key secundaria (OPENROUTER_FREE_KEY / DEEPINFRA_FREE_KEY).

El enrutador NO altera el proveedor por defecto: solo cambia el flujo cuando
el modo libre está explícitamente activado, y respeta siempre el sandbox y
las claves de entorno del servidor.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# Modelos sin restricciones de sistema (catálogo por defecto del Modo Libre).
DEFAULT_FREE_MODELS: Dict[str, str] = {
    "openrouter": "cognitivecomputations/dolphin-mixtral-8x7b",
    "deepinfra": "cognitivecomputations/dolphin-2.7-mixtral-8x7b",
}


class MultiModelRouter:
    """Capa de enrutamiento que decide el proveedor/modelo según el modo."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        # Catálogo de modelos libres sobreescribible por env.
        self.free_models = {
            "openrouter": os.getenv(
                "OPENROUTER_FREE_MODEL",
                DEFAULT_FREE_MODELS["openrouter"],
            ),
            "deepinfra": os.getenv(
                "DEEPINFRA_FREE_MODEL",
                DEFAULT_FREE_MODELS["deepinfra"],
            ),
        }
        # Proveedores extra que el router puede activar.
        self.extra_providers = {
            "deepinfra": {
                "url": os.getenv("DEEPINFRA_BASE_URL", "https://api.deepinfra.com/v1"),
                "model": self.free_models["deepinfra"],
                "api_key": os.getenv("DEEPINFRA_API_KEY") or os.getenv("DEEPINFRA_FREE_KEY"),
                "timeout": int(os.getenv("DEEPINFRA_TIMEOUT", "40")),
            },
        }

    def free_mode_available(self) -> bool:
        """True si hay al menos una API key secundaria configurada."""
        return bool(
            os.getenv("OPENROUTER_FREE_KEY")
            or os.getenv("DEEPINFRA_API_KEY")
            or os.getenv("DEEPINFRA_FREE_KEY")
            or os.getenv("OPENROUTER_API_KEY")
        )

    def list_providers(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for name, cfg in self.engine.providers.items():
            out.append(
                {
                    "provider": name,
                    "model": cfg["model"],
                    "configured": bool(cfg.get("api_key")),
                }
            )
        for name, cfg in self.extra_providers.items():
            out.append(
                {
                    "provider": name,
                    "model": cfg["model"],
                    "configured": bool(cfg.get("api_key")),
                }
            )
        return out

    def chat(
        self,
        prompt: str,
        context: Optional[str] = None,
        free_mode: bool = False,
        prefer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Envía el chat. Si ``free_mode`` está activo, usa modelo sin censura."""
        if not free_mode:
            return self.engine.chat(prompt=prompt, context=context)
        if not self.free_mode_available():
            return {
                "text": (
                    "Modo Libre no disponible: falta API key secundaria "
                    "(OPENROUTER_FREE_KEY / DEEPINFRA_API_KEY)."
                ),
                "provider": "none",
                "free_mode": False,
            }
        # Elegir proveedor libre (preferencia explícita o el primero con key).
        provider = self._pick_free_provider(prefer)
        if provider is None:
            return {
                "text": "Ningún proveedor del Modo Libre está configurado.",
                "provider": "none",
                "free_mode": True,
            }
        cfg = (
            self.extra_providers[provider]
            if provider in self.extra_providers
            else self.engine.providers[provider]
        )
        try:
            return self._call_openai_compat(provider, cfg, prompt, context)
        except Exception as exc:  # pragma: no cover
            return {
                "text": f"Free-mode error: {exc}",
                "error": str(exc),
                "provider": provider,
                "free_mode": True,
            }

    def _pick_free_provider(self, prefer: Optional[str]) -> Optional[str]:
        candidates = []
        if prefer and (
            prefer in self.extra_providers or prefer in self.engine.providers
        ):
            candidates.append(prefer)
        # Orden por defecto: openrouter (key secundaria) -> deepinfra.
        if os.getenv("OPENROUTER_FREE_KEY") or os.getenv("OPENROUTER_API_KEY"):
            candidates.append("openrouter")
        if os.getenv("DEEPINFRA_API_KEY") or os.getenv("DEEPINFRA_FREE_KEY"):
            candidates.append("deepinfra")
        for c in candidates:
            cfg = (
                self.extra_providers.get(c) or self.engine.providers.get(c)
            )
            if cfg and cfg.get("api_key"):
                return c
        return None

    def _call_openai_compat(
        self, provider: str, cfg: Dict[str, Any], prompt: str, context: Optional[str]
    ) -> Dict[str, Any]:
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        session = self.engine.session
        url = f"{cfg['url'].rstrip('/')}/chat/completions"
        msgs = []
        if context:
            msgs.append({"role": "system", "content": context})
        msgs.append({"role": "user", "content": prompt})
        payload = {
            "model": cfg["model"],
            "messages": msgs,
            "temperature": 0.9,
            "max_tokens": 2048,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if cfg.get("api_key"):
            headers["Authorization"] = f"Bearer {cfg['api_key']}"
        r = session.post(url, json=payload, headers=headers, timeout=cfg["timeout"])
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices") or []
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        return {
            "text": text,
            "provider": provider,
            "model": cfg["model"],
            "free_mode": True,
        }
