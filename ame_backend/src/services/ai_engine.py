"""
AURA AI Engine
Servicio unificado para orquestar múltiples proveedores de IA.
"""

from __future__ import annotations

import base64
import json
import os
import re
import requests
import time
from typing import Any, Dict, List, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from ame_backend.src.tools import workspace as _workspace
except Exception:  # pragma: no cover
    _workspace = None  # type: ignore

_SYSTEM_INTENT_CONTEXT = (
    "You are an intent parser for AURA. If the user asks to start or run any monetization bot, "
    "reply ONLY with a JSON object like: "
    '{"action": "START_BOT", "target": "<target>"} . '
    "Valid targets: surveys. "
    "For any other message, reply normally as AURA assistant."
)


class AIEngine:
    def __init__(self) -> None:
        self.providers = {
            "gemini": {
                "url": os.getenv(
                    "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
                ),
                "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
                "api_key": os.getenv("GEMINI_API_KEY"),
                "timeout": int(os.getenv("GEMINI_TIMEOUT", "30")),
            },
            "groq": {
                "url": "https://api.groq.com/openai/v1",
                "model": "llama-3.3-70b-versatile",
                "api_key": os.getenv("GROQ_API_KEY"),
                "timeout": int(os.getenv("GROQ_TIMEOUT", "30")),
            },
            "openrouter": {
                "url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                "model": os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3-8b-instruct:free"),
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "timeout": int(os.getenv("OPENROUTER_TIMEOUT", "30")),
            },
            "lm_studio": {
                "url": os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
                "model": os.getenv("LM_STUDIO_MODEL", "gemma-2-2b-it"),
                "api_key": None,
                "timeout": int(os.getenv("LM_STUDIO_TIMEOUT", "60")),
            },
            "local_lfm": {
                "url": os.getenv("LOCAL_LFM_BASE_URL", "http://ai-engine-local:11434"),
                "model": os.getenv("LOCAL_LFM_MODEL", "lfm2.5:latest"),
                "api_key": None,
                "timeout": int(os.getenv("LOCAL_LFM_TIMEOUT", "120")),
            },
            "huggingface": {
                "url": "https://api-inference.huggingface.co/models",
                "model": os.getenv("HF_MODEL", "google/gemma-2-9b-it"),
                "api_key": os.getenv("HF_TOKEN"),
                "timeout": int(os.getenv("HF_TIMEOUT", "60")),
            },
        }
        self.preference = os.getenv(
            "AI_PROVIDER_PREFERENCE", "auto"
        )  # auto | gemini | groq | openrouter | lm_studio | local_lfm
        self.session = self._build_session()
        self._intent_pattern = re.compile(
            r"(?:inicia|arranca|empieza|start|run|activa)\s+(?:el\s+)?(?:bot\s+)?(?:de\s+)?(?:las\s+)?(?:encuestas|survey|granja|farm)",
            re.IGNORECASE,
        )

    def _build_session(self) -> requests.Session:
        s = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 502, 503, 504])
        s.mount("https://", HTTPAdapter(max_retries=retries))
        s.mount("http://", HTTPAdapter(max_retries=retries))
        return s

    def _headers(self, provider: str) -> Dict[str, str]:
        key = self.providers[provider]["api_key"]
        h = {"Content-Type": "application/json"}
        if provider == "lm_studio":
            return h
        if key:
            h["Authorization"] = f"Bearer {key}"
        if provider == "openrouter":
            h["HTTP-Referer"] = "https://ame-backend.local"
            h["X-Title"] = "AURA Backend"
        return h

    def chat(
        self,
        prompt: str,
        context: Optional[str] = None,
        model_override: Optional[str] = None,
        provider_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        intent_json = self._try_intent_command(prompt)
        if intent_json is not None:
            return {
                "text": json.dumps(intent_json),
                "intent": intent_json,
                "provider": "local_parser",
            }
        return self._chat_ai(
            prompt=prompt,
            context=context,
            model_override=model_override,
            provider_override=provider_override,
        )

    def _try_intent_command(self, prompt: str) -> Optional[Dict[str, Any]]:
        if not self._intent_pattern.search(prompt or ""):
            return None
        return {"action": "START_BOT", "target": "surveys"}

    def _chat_ai(
        self,
        prompt: str,
        context: Optional[str] = None,
        model_override: Optional[str] = None,
        provider_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        effective_context = _SYSTEM_INTENT_CONTEXT
        if context:
            effective_context = f"{context}\n\n{_SYSTEM_INTENT_CONTEXT}"
        providers = self._resolve_providers(provider_override)
        last_error: Optional[Exception] = None
        for provider in providers:
            try:
                return self._call_provider(
                    provider,
                    prompt,
                    effective_context,
                    model_override,
                )
            except Exception as e:
                last_error = e
                status = getattr(e, "response", None) and getattr(e.response, "status_code", None)
                if status in (429, 500, 502, 503, 504):
                    try:
                        return self._call_provider(
                            "huggingface",
                            prompt,
                            effective_context,
                            model_override,
                        )
                    except Exception as hf_exc:
                        logger.error("Fallback Hugging Face falló: %s", hf_exc)
                        last_error = hf_exc
        return {
            "text": f"AI error: {last_error}",
            "error": str(last_error) if last_error else "Unknown error",
            "provider": "none",
        }

    def _resolve_providers(self, override: Optional[str]) -> list:
        if override and override in self.providers:
            return [override]
        if self.preference != "auto":
            if self.preference in self.providers:
                return [self.preference] + [p for p in self.providers if p != self.preference]
        return list(self.providers.keys())

    def vision(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        context: Optional[str] = None,
        model_override: Optional[str] = None,
        provider_override: Optional[str] = "gemini",
    ) -> Dict[str, Any]:
        """Analisis multimodal nativo: texto + imagen via Gemini 2.0 Flash."""
        if not image_bytes:
            return {"text": "No se recibio imagen.", "provider": "none"}
        providers = self._resolve_providers(provider_override)
        last_error: Optional[Exception] = None
        for provider in providers:
            try:
                cfg = self.providers[provider]
                if provider == "gemini":
                    return self._call_gemini_vision(
                        cfg, prompt, image_bytes, mime_type, context, model_override
                    )
                # Fallback: descripción base si el proveedor no es multimodal.
                return {
                    "text": "(Proveedor sin vision nativa; se requiere Gemini para imagenes)",
                    "provider": provider,
                }
            except Exception as e:
                last_error = e
        return {
            "text": f"Vision error: {last_error}",
            "error": str(last_error) if last_error else "Unknown error",
            "provider": "none",
        }

    def _call_gemini_vision(
        self, cfg, prompt, image_bytes, mime_type, context, model_override
    ) -> Dict[str, Any]:
        url = (
            f"{cfg['url']}/models/{model_override or cfg['model']}"
            f":generateContent?key={cfg['api_key']}"
        )
        payload = {
            "contents": self._contents_multimodal(
                prompt, image_bytes, mime_type, context
            )
        }
        r = self.session.post(url, json=payload, timeout=cfg["timeout"])
        r.raise_for_status()
        data = r.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return {"text": "", "raw": data, "provider": "gemini"}
        text = (
            candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        )
        return {"text": text, "provider": "gemini"}

    def _call_provider(
        self,
        provider: str,
        prompt: str,
        context: Optional[str],
        model_override: Optional[str],
    ) -> Dict[str, Any]:
        cfg = self.providers[provider]
        if provider == "gemini":
            return self._call_openai_compat(
                f"{cfg['url']}/models/{model_override or cfg['model']}:generateContent?key={cfg['api_key']}",
                {"contents": self._contents(prompt, context)},
            )
        if provider == "huggingface":
            return self._call_huggingface(cfg, prompt, context, model_override)
        if provider in ("groq", "openrouter", "lm_studio", "local_lfm"):
            return self._call_openai_compat(
                f"{cfg['url']}/chat/completions",
                {
                    "model": model_override or cfg["model"],
                    "messages": self._messages(prompt, context),
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "stream": False,
                },
            )
        raise ValueError(f"Unknown provider: {provider}")

    def _call_openai_compat(self, url: str, payload: dict) -> Dict[str, Any]:
        r = self.session.post(url, json=payload, headers=self._headers_for_url(url), timeout=30)
        r.raise_for_status()
        data = r.json()
        candidates = data.get("candidates") or data.get("choices") or []
        if not candidates:
            return {"text": "", "raw": data}
        if "content" in candidates[0]:
            text = candidates[0]["content"].get("parts", [{}])[0].get("text", "")
        else:
            text = candidates[0].get("message", {}).get("content", "")
        return {"text": text, "raw": data}

    def _call_huggingface(
        self,
        cfg: Dict[str, Any],
        prompt: str,
        context: Optional[str],
        model_override: Optional[str],
    ) -> Dict[str, Any]:
        url = f"{cfg['url']}/{model_override or cfg['model']}"
        payload = {
            "inputs": f"{context}\n\n{prompt}" if context else prompt,
            "parameters": {"max_new_tokens": 1024, "temperature": 0.7, "return_full_text": False},
        }
        headers = {"Content-Type": "application/json"}
        api_key = cfg.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        r = self.session.post(url, json=payload, headers=headers, timeout=cfg["timeout"])
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            text = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            text = data.get("generated_text", "") or data.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            text = ""
        return {"text": text.strip(), "provider": "huggingface"}

    def query_hf_inference(
        self, prompt: str, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Consulta la API de Inferencia Serverless de Hugging Face."""
        cfg = self.providers["huggingface"]
        return self._call_huggingface(cfg, prompt, None, model)

    def _headers_for_url(self, url: str) -> dict:
        if "/generateContent" in url:
            return {"Content-Type": "application/json"}
        if "lm_studio" in url or "localhost" in url or "127.0.0.1" in url:
            return {"Content-Type": "application/json"}
        return self._headers("openrouter")

    def _contents(self, prompt: str, context: Optional[str]) -> list:
        parts = []
        if context:
            parts.append({"text": context})
        parts.append({"text": prompt})
        return [{"parts": parts}]

    def _contents_multimodal(
        self, prompt: str, image_bytes: bytes, mime_type: str, context: Optional[str] = None
    ) -> list:
        """Contenido multimodal nativo de Gemini: texto + imagen inline."""
        parts = []
        if context:
            parts.append({"text": context})
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(image_bytes).decode("ascii"),
                }
            }
        )
        parts.append({"text": prompt})
        return [{"parts": parts}]

    def _messages(self, prompt: str, context: Optional[str]) -> list:
        msgs = []
        if context:
            msgs.append({"role": "system", "content": context})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    # ------------------------------------------------------------------ #
    # Tool Calling nativo (Gemini): AURA opera archivos del workspace
    # ------------------------------------------------------------------ #
    def chat_with_tools(
        self,
        prompt: str,
        context: Optional[str] = None,
        provider_override: Optional[str] = None,
        max_tool_rounds: int = 4,
    ) -> Dict[str, Any]:
        """Chat con Tool Calling nativo de Gemini.

        Gemini decide cuándo invocar las herramientas de workspace
        (read/list/write). Los resultados se re-inyectan como ``functionResponse``
        y AURA responde con el contexto del archivo ya cargado. Si el proveedor
        no soporta tools o falla, degrade a ``chat`` normal.
        """
        if _workspace is None:
            return self.chat(prompt=prompt, context=context)
        providers = self._resolve_providers(provider_override)
        last_error: Optional[Exception] = None
        for provider in providers:
            if provider != "gemini":
                continue  # Tool calling nativo solo en Gemini.
            try:
                return self._gemini_tool_loop(
                    prompt, context, max_tool_rounds
                )
            except Exception as e:
                last_error = e
        # Fallback: chat sin tools.
        base = self.chat(prompt=prompt, context=context)
        if last_error:
            base["tool_error"] = str(last_error)
        return base

    def _gemini_tool_loop(
        self, prompt: str, context: Optional[str], max_tool_rounds: int
    ) -> Dict[str, Any]:
        cfg = self.providers["gemini"]
        url = (
            f"{cfg['url']}/models/{cfg['model']}"
            f":generateContent?key={cfg['api_key']}"
        )
        tools = [{"functionDeclarations": _workspace.GEMINI_TOOL_DECLARATIONS}]
        # Historial de contenidos (acumula llamadas y respuestas).
        sys_text = context or "Eres AURA, asistente con manos en el workspace local."
        contents: List[Dict[str, Any]] = [
            {
                "role": "user",
                "parts": [{"text": f"{sys_text}\n\n{prompt}"}],
            }
        ]
        tool_log: List[Dict[str, Any]] = []
        for _ in range(max_tool_rounds):
            payload = {
                "contents": contents,
                "tools": tools,
                "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}},
            }
            r = self.session.post(url, json=payload, timeout=cfg["timeout"])
            r.raise_for_status()
            data = r.json()
            candidates = data.get("candidates") or []
            if not candidates:
                return {
                    "text": "",
                    "raw": data,
                    "provider": "gemini",
                    "tool_calls": tool_log,
                }
            cand = candidates[0]
            parts = cand.get("content", {}).get("parts", [])
            # ¿Hay llamadas a funciones?
            calls = [p for p in parts if p.get("functionCall")]
            if not calls:
                text = parts[0].get("text", "") if parts else ""
                return {
                    "text": text,
                    "provider": "gemini",
                    "tool_calls": tool_log,
                }
            # Ejecutar cada tool call y acumular functionResponse.
            resp_parts: List[Dict[str, Any]] = []
            for call in calls:
                fc = call["functionCall"]
                name = fc.get("name")
                args = fc.get("args", {}) or {}
                result = _workspace.dispatch_tool(name, args)
                tool_log.append({"tool": name, "args": args, "result": result})
                resp_parts.append(
                    {
                        "functionResponse": {
                            "name": name,
                            "response": {"result": result},
                        }
                    }
                )
            # Añadir el turno del modelo (con las calls) y la respuesta de la tool.
            contents.append({"role": "model", "parts": parts})
            contents.append({"role": "user", "parts": resp_parts})
        return {
            "text": "(límite de rondas de herramientas alcanzado)",
            "provider": "gemini",
            "tool_calls": tool_log,
        }

    def health_check(self) -> Dict[str, Any]:
        status = {}
        for name, cfg in self.providers.items():
            try:
                start = time.time()
                if name == "lm_studio":
                    url = cfg["url"].rstrip("/") + "/models"
                else:
                    url = cfg["url"].rstrip("/")
                r = self.session.get(url, timeout=5)
                ok = r.status_code < 400
                status[name] = {
                    "ok": ok,
                    "latency_ms": round((time.time() - start) * 1000),
                    "status": r.status_code,
                }
            except Exception as e:
                status[name] = {"ok": False, "error": str(e)}
        return status
