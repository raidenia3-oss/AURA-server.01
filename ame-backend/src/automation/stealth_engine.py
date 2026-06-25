"""
Stealth engine for AURA backend.
Infiltrator class using Playwright with advanced evasion configurations.
"""

from __future__ import annotations

import asyncio
import random
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


class Infiltrator:
    def __init__(self) -> None:
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        ]
        self._current_ua = random.choice(self._user_agents)

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-webdriver",
                "--disable-extensions",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-webgl",
                "--disable-canvas-aa",
                "--disable-2d-canvas-clip-aa",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-translate",
                "--disable-background-networking",
                "--disable-default-apps",
                "--metrics-reporter-disabled",
                "--mute-audio",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=self._current_ua,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "DNT": "1",
            },
        )
        self._page = await self._context.new_page()
        await self._page.set_extra_http_headers(
            {
                "User-Agent": self._current_ua,
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    async def stop(self) -> None:
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None

    async def rotate_user_agent(self) -> None:
        self._current_ua = random.choice(self._user_agents)
        if self._context:
            await self._context.set_user_agent(self._current_ua)
        if self._page:
            await self._page.set_extra_http_headers(
                {
                    "User-Agent": self._current_ua,
                }
            )

    @staticmethod
    def _jitter(base_ms: int = 500, variance_ms: int = 1000) -> int:
        return base_ms + random.randint(0, variance_ms)

    async def _wait_human(self) -> None:
        delay = self._jitter(300, 800)
        await asyncio.sleep(delay / 1000)

    async def smart_navigate(self, url: str) -> None:
        if not self._page:
            raise RuntimeError("Infiltrator not started")
        await self._wait_human()
        await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(0.5)
        try:
            await self._page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

    async def smart_click(self, text_or_selector: str) -> None:
        if not self._page:
            raise RuntimeError("Infiltrator not started")
        await self._wait_human()
        selector = f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text_or_selector.lower()}')] | //a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text_or_selector.lower()}')] | //input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text_or_selector.lower()}')] | [aria-label*='{text_or_selector}' i] | [title*='{text_or_selector}' i] | {text_or_selector}"
        try:
            await self._page.click(selector, timeout=10000)
        except Exception:
            try:
                await self._page.click(text_or_selector, timeout=5000)
            except Exception as e:
                raise RuntimeError(f"smart_click failed for '{text_or_selector}': {e}")

    async def smart_type(self, selector: str, text: str) -> None:
        if not self._page:
            raise RuntimeError("Infiltrator not started")
        await self._wait_human()
        await self._page.focus(selector)
        for ch in text:
            await self._page.type(selector, ch, delay=random.randint(50, 200))
        await asyncio.sleep(0.2)

    async def extract_context(self) -> str:
        if not self._page:
            raise RuntimeError("Infiltrator not started")
        await self._wait_human()
        html = await self._page.content()
        text = await self._page.evaluate("""() => {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            const parts = [];
            let node;
            while (node = walker.nextNode()) {
                const p = node.parentElement;
                if (!p) continue;
                const s = window.getComputedStyle(p);
                const hidden = s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0' || p.hasAttribute('hidden');
                if (!hidden && node.textContent && node.textContent.trim()) {
                    parts.push(node.textContent.trim());
                }
            }
            return parts.join('\\n');
        }""")
        return text.strip()

    @property
    def page(self) -> Optional[Page]:
        return self._page
