"""
run_production.py — AURA-server.01
Production startup wrapper.

Replaces the Flask development server with Gunicorn, wires up log
sanitisation and environment validation, then hands off to Gunicorn
which imports the Flask app from AME_Core/servidor_ame.py.

Usage (set by railway.toml):
    python run_production.py
"""

import os
import sys
import logging
import multiprocessing

# ── 1. Install log sanitisation FIRST — before any key is loaded ─────────────
# This ensures that even if a key leaks into a print() or log call during
# import, it is masked before reaching stdout/stderr.
from log_sanitizer import install_all
install_all()

# ── 2. Validate / inject environment variables ────────────────────────────────
from env_validator import validate_env
validation = validate_env(load_dotenv=True)

# ── 3. Basic logging setup ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("aura.production")

logger.info("=" * 60)
logger.info("🚀  AURA-server.01 — Production startup")
logger.info("🔑  API key validation: %s", validation["status"].upper())
logger.info(
    "    Present: %d/%d  |  Missing: %s",
    len(validation["keys_present"]),
    validation["total_keys"],
    ", ".join(validation["keys_missing"]) or "none",
)

# ── 4. Gunicorn configuration ─────────────────────────────────────────────────
PORT = int(os.environ.get("PORT", 8080))

# Worker count: (2 × CPU cores) + 1 is the standard Gunicorn recommendation.
# Cap at 4 to avoid memory pressure on small Railway instances.
_cpu_count = multiprocessing.cpu_count()
WORKERS = min((_cpu_count * 2) + 1, 4)

# Use gthread worker class for async-friendly concurrency without requiring
# an event loop.  Each worker gets THREADS threads so WebSocket-style
# long-polling requests don't starve other connections.
WORKER_CLASS = "gthread"
THREADS = 4

# The Flask application object lives inside AME_Core/servidor_ame.py.
# Gunicorn needs it as "module:attribute".  We add AME_Core to sys.path
# so the module can be imported without the directory prefix.
AME_CORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AME_Core")
if AME_CORE_DIR not in sys.path:
    sys.path.insert(0, AME_CORE_DIR)

APP_MODULE = "servidor_ame:app"

logger.info("⚙️   Workers: %d × %s  |  Threads/worker: %d", WORKERS, WORKER_CLASS, THREADS)
logger.info("📡  Binding:  0.0.0.0:%d", PORT)
logger.info("=" * 60)

# ── 5. Launch Gunicorn programmatically ──────────────────────────────────────
try:
    from gunicorn.app.base import BaseApplication

    class StandaloneApplication(BaseApplication):
        """Minimal Gunicorn application wrapper."""

        def __init__(self, app_uri: str, options: dict | None = None):
            self.app_uri = app_uri
            self.options = options or {}
            super().__init__()

        def load_config(self):
            for key, value in self.options.items():
                if key in self.cfg.settings and value is not None:
                    self.cfg.set(key.lower(), value)

        def load(self):
            # Import the Flask app object
            module_name, attr = self.app_uri.split(":")
            import importlib
            module = importlib.import_module(module_name)
            return getattr(module, attr)

    gunicorn_options = {
        "bind":         f"0.0.0.0:{PORT}",
        "workers":      WORKERS,
        "worker_class": WORKER_CLASS,
        "threads":      THREADS,
        # Timeouts
        "timeout":      120,        # worker silent timeout (seconds)
        "graceful_timeout": 30,     # time to finish in-flight requests on SIGTERM
        "keepalive":    5,          # keep-alive connections
        # Logging — forward to Python's logging so our sanitiser catches it
        "accesslog":    "-",        # stdout
        "errorlog":     "-",        # stderr
        "loglevel":     "info",
        # Reload disabled in production
        "reload":       False,
        # Preload the app in the master process to share memory across workers
        "preload_app":  True,
    }

    StandaloneApplication(APP_MODULE, gunicorn_options).run()

except ImportError:
    # Gunicorn is not available (e.g. local Windows dev environment).
    # Fall back to Flask's built-in server with a loud warning.
    logger.warning(
        "⚠️  Gunicorn not found — falling back to Flask development server. "
        "Install gunicorn>=21.0 for production use."
    )
    import importlib
    module = importlib.import_module("servidor_ame")
    flask_app = module.app
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
