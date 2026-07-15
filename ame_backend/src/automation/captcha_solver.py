"""
Captcha solving stub for the AME stealth browser.

This module is a placeholder for the captcha-solving integration used by
``stealth_browser.py``. Implement the real solver (e.g. a captcha-solving
service or ML model) in Phase 58 and replace ``solve_challenge``.
"""

from __future__ import annotations

from typing import Optional


async def solve_challenge(
    site_key: str,
    page_url: str,
    captcha_type: str = "recaptcha",
) -> Optional[str]:
    """Solve a captcha challenge and return the token, or ``None``.

    Args:
        site_key: The site/public key of the captcha widget.
        page_url: The URL where the captcha is rendered.
        captcha_type: ``"recaptcha"``, ``"hcaptcha"``, etc.

    Returns:
        The solved token string, or ``None`` if unsolved/not implemented.
    """
    raise NotImplementedError(
        "captcha_solver.solve_challenge is not implemented yet "
        "(wire up a captcha-solving provider in Phase 58)"
    )
