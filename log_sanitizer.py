"""
log_sanitizer.py — AURA-server.01
Masks sensitive values (API keys, tokens) in all log output before it
reaches stdout/stderr.  Integrates with Python's logging module and
wraps sys.stdout / sys.stderr so that Gunicorn's own print() calls are
also sanitised.
"""

import re
import sys
import logging
import os
from typing import List

# ── Patterns that identify sensitive values ──────────────────────────────────
# Each tuple is (compiled_regex, replacement_label).
# Order matters: more-specific patterns first.
_RAW_PATTERNS: List[tuple] = [
    # OpenRouter  sk-or-v1-<hex>
    (r"sk-or-v1-[A-Za-z0-9]{10,}", "sk-or-v1-***REDACTED***"),
    # DeepSeek    sk-<hex>
    (r"sk-[A-Za-z0-9]{10,}", "sk-***REDACTED***"),
    # Groq        gsk_<base62>
    (r"gsk_[A-Za-z0-9]{10,}", "gsk_***REDACTED***"),
    # Mistral     csk-<base62>
    (r"csk-[A-Za-z0-9]{10,}", "csk-***REDACTED***"),
    # Cerebras    U75C<base62>  (starts with U75C)
    (r"U75C[A-Za-z0-9]{6,}", "U75C***REDACTED***"),
    # Google / Gemini  AIza<base62>
    (r"AIza[A-Za-z0-9_\-]{10,}", "AIza***REDACTED***"),
    # Generic Bearer tokens in HTTP headers
    (r"(?i)(bearer\s+)[A-Za-z0-9\-_\.]{20,}", r"\1***REDACTED***"),
    # Generic "key=<value>" patterns (query-string style)
    (r"(?i)(api[_-]?key[=:]\s*)[A-Za-z0-9\-_\.]{16,}", r"\1***REDACTED***"),
]

_COMPILED: List[tuple] = [
    (re.compile(pattern), replacement)
    for pattern, replacement in _RAW_PATTERNS
]


def sanitize(text: str) -> str:
    """Return *text* with all sensitive patterns replaced."""
    for pattern, replacement in _COMPILED:
        text = pattern.sub(replacement, text)
    return text


# ── Logging filter ────────────────────────────────────────────────────────────

class SanitizingFilter(logging.Filter):
    """Logging filter that scrubs sensitive data from every log record."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        # Sanitise the formatted message
        record.msg = sanitize(str(record.msg))
        # Sanitise any string arguments
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: sanitize(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


# ── Stream wrapper ────────────────────────────────────────────────────────────

class SanitizingStream:
    """
    Wraps a file-like stream (stdout / stderr) and sanitises every
    write() call before forwarding it to the underlying stream.
    """

    def __init__(self, wrapped):
        self._wrapped = wrapped

    def write(self, text: str) -> int:
        return self._wrapped.write(sanitize(text))

    def flush(self):
        self._wrapped.flush()

    def fileno(self):
        return self._wrapped.fileno()

    # Forward any other attribute access to the wrapped stream
    def __getattr__(self, name):
        return getattr(self._wrapped, name)


# ── Public install helpers ────────────────────────────────────────────────────

def install_log_filter(logger: logging.Logger | None = None) -> None:
    """
    Attach *SanitizingFilter* to *logger* (defaults to the root logger)
    and to every handler already attached to it.
    """
    target = logger or logging.getLogger()
    f = SanitizingFilter()
    target.addFilter(f)
    for handler in target.handlers:
        handler.addFilter(f)


def install_stream_wrappers() -> None:
    """
    Replace sys.stdout and sys.stderr with sanitising wrappers so that
    plain print() calls (e.g. from Gunicorn or third-party code) are
    also sanitised before reaching the terminal / deployment log.
    """
    if not isinstance(sys.stdout, SanitizingStream):
        sys.stdout = SanitizingStream(sys.stdout)
    if not isinstance(sys.stderr, SanitizingStream):
        sys.stderr = SanitizingStream(sys.stderr)


def install_all(logger: logging.Logger | None = None) -> None:
    """
    Convenience function: install both the logging filter and the stream
    wrappers in one call.  Call this as early as possible in the process
    lifecycle, before any keys are loaded into memory.
    """
    install_stream_wrappers()
    install_log_filter(logger)
    # Also attach to the 'gunicorn' and 'gunicorn.error' loggers if they
    # exist (they are created lazily by Gunicorn workers).
    for name in ("gunicorn", "gunicorn.error", "gunicorn.access"):
        lg = logging.getLogger(name)
        f = SanitizingFilter()
        lg.addFilter(f)
        for handler in lg.handlers:
            handler.addFilter(f)
