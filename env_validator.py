"""
env_validator.py — AURA-server.01
Validates critical API keys at startup, provides secure mock fallbacks
for missing keys, and exposes a validation summary for health checks.
Actual key values are never written to logs — only presence/absence.
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ── Key registry ──────────────────────────────────────────────────────────────
# Maps environment variable name → mock fallback value used when the key
# is absent.  The fallback keeps the app from crashing while making it
# obvious in API responses that a real key is missing.
_KEY_REGISTRY: Dict[str, str] = {
    "OPENROUTER_API_KEY": "mock-key-openrouter",
    "DEEPSEEK_API_KEY":   "mock-key-deepseek",
    "GROQ_API_KEY":       "mock-key-groq",
    "MISTRAL_API_KEY":    "mock-key-mistral",
    "CEREBRAS_API_KEY":   "mock-key-cerebras",
    "GEMINI_API_KEY":     "mock-key-gemini",
}

# Populated by validate_env(); consumed by get_validation_status()
_validation_result: Dict[str, Any] = {}


def validate_env(load_dotenv: bool = True) -> Dict[str, Any]:
    """
    Check every key in *_KEY_REGISTRY*.

    For each key:
      - If present in the environment → mark as "present" (value untouched).
      - If absent → inject the mock fallback and mark as "missing".

    Returns a dict suitable for embedding in /health responses.
    Never logs actual key values.
    """
    global _validation_result

    if load_dotenv:
        try:
            from dotenv import load_dotenv as _load
            _load(override=False)   # don't override keys already in the env
        except ImportError:
            pass  # python-dotenv not installed; rely on real env vars

    present: list[str] = []
    missing: list[str] = []

    for key, mock_value in _KEY_REGISTRY.items():
        value = os.environ.get(key, "").strip()
        if value and not value.startswith("mock-key-"):
            present.append(key)
            logger.info("[env_validator] ✅  %s — present", key)
        else:
            # Inject mock so downstream code doesn't crash on a missing key
            os.environ[key] = mock_value
            missing.append(key)
            logger.warning(
                "[env_validator] ⚠️  %s — missing, using secure mock fallback",
                key,
            )

    all_present = len(missing) == 0
    status = "ok" if all_present else ("degraded" if present else "critical")

    _validation_result = {
        "status":        status,
        "all_keys_present": all_present,
        "keys_present":  present,
        "keys_missing":  missing,
        "total_keys":    len(_KEY_REGISTRY),
    }

    if all_present:
        logger.info(
            "[env_validator] All %d API keys validated successfully.",
            len(_KEY_REGISTRY),
        )
    else:
        logger.warning(
            "[env_validator] %d/%d API keys missing — mock fallbacks active: %s",
            len(missing),
            len(_KEY_REGISTRY),
            ", ".join(missing),
        )

    return _validation_result


def get_validation_status() -> Dict[str, Any]:
    """
    Return the cached result of the last validate_env() call.
    If validate_env() has not been called yet, run it now.
    """
    if not _validation_result:
        return validate_env()
    return _validation_result
