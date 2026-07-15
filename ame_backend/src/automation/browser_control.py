"""Browser-control skill for AME.

Gives AURA/AME programmatic control over a (headless) browser using
Playwright. Playwright is imported lazily so this module loads even when the
dependency is not installed; the methods return a clear error in that case.
This is the server-side counterpart of the in-page control panel in the
frontend (``/skills/browser-control``).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional


class BrowserControl:
    """Drive a Chromium browser to navigate, read and interact with pages."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._page = None

    @staticmethod
    def available() -> bool:
        try:
            import playwright  # noqa: F401

            return True
        except Exception:
            return False

    async def _ensure(self) -> None:
        if self._page is not None:
            return
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._page = await self._browser.new_page()

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._browser = None
        self._playwright = None

    async def run(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available():
            return {
                "ok": False,
                "error": (
                    "Playwright no instalado. Ejecuta: "
                    "pip install playwright && playwright install chromium"
                ),
            }
        try:
            handler = {
                "navigate": self._navigate,
                "extract_text": self._extract_text,
                "click": self._click,
                "fill": self._fill,
                "evaluate": self._evaluate,
                "screenshot": self._screenshot,
            }.get(action)
            if handler is None:
                return {"ok": False, "error": f"Accion desconocida: {action}"}
            return await handler(payload)
        finally:
            await self.close()

    async def _navigate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure()
        url = str(payload.get("url", ""))
        if not url:
            return {"ok": False, "error": "Falta 'url'"}
        await self._page.goto(url, wait_until="domcontentloaded")
        return {"ok": True, "action": "navigate", "url": self._page.url}

    async def _extract_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure()
        selector = payload.get("selector")
        if selector:
            text = await self._page.locator(selector).first.inner_text()
        else:
            text = await self._page.evaluate("document.body.innerText")
        return {
            "ok": True,
            "action": "extract_text",
            "text": str(text)[:5000],
        }

    async def _click(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure()
        selector = str(payload.get("selector", ""))
        if not selector:
            return {"ok": False, "error": "Falta 'selector'"}
        await self._page.locator(selector).first.click()
        return {"ok": True, "action": "click", "selector": selector}

    async def _fill(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure()
        selector = str(payload.get("selector", ""))
        value = str(payload.get("value", ""))
        if not selector:
            return {"ok": False, "error": "Falta 'selector'"}
        await self._page.locator(selector).first.fill(value)
        return {"ok": True, "action": "fill", "selector": selector, "value": value}

    async def _evaluate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure()
        js = str(payload.get("js", ""))
        if not js:
            return {"ok": False, "error": "Falta 'js'"}
        result = await self._page.evaluate(js)
        return {"ok": True, "action": "evaluate", "result": result}

    async def _screenshot(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        await self._ensure()
        import base64

        buf = await self._page.screenshot(full_page=bool(payload.get("full", False)))
        return {
            "ok": True,
            "action": "screenshot",
            "data_base64": base64.b64encode(buf).decode("utf-8"),
        }


def run_sync(action: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience synchronous wrapper."""
    return asyncio.run(BrowserControl().run(action, payload or {}))
