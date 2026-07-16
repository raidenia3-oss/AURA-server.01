"""
AURA Autonomous Config Agent

Detects the environment, creates local config files, installs Python deps,
starts the backend service and verifies its health. Frontend local startup is
documented but not launched here because the installed Next.js (9.3.3) cannot
run the App Router code; the frontend is deployed on Vercel.

Corrected vs. the original plan:
- Backend is launched as a module: ``python -m ame_backend.src.main``
  (running the file directly raises ModuleNotFoundError on package imports).
- Health is checked at ``/health`` (there is no ``/api/health`` route).
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
import platform
import time
import socket
from typing import Any, Dict, Optional
from datetime import datetime


class AuraConfigAgent:
    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.log: list[str] = []
        self.errors: list[str] = []
        self.services: Dict[str, Optional[subprocess.Popen]] = {}
        self.local_ip = self._get_local_ip()

    # ─────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────
    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"

    def log_info(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        full = f"[{ts}] [+] {msg}"
        self.log.append(full)
        print(full, flush=True)

    def log_error(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        full = f"[{ts}] [x] {msg}"
        self.errors.append(full)
        print(full, file=sys.stderr, flush=True)

    def log_warning(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        full = f"[{ts}] [!] {msg}"
        self.log.append(full)
        print(full, flush=True)

    # ─────────────────────────────────────
    # Detection
    # ─────────────────────────────────────
    def detect_os(self) -> str:
        name = platform.system()
        self.config["os"] = name
        self.log_info(f"OS detected: {name}")
        return name

    def detect_python(self) -> bool:
        try:
            result = subprocess.run(
                ["python", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = (result.stdout or result.stderr).strip()
            self.config["python"] = version
            self.log_info(f"Python: {version}")
            return True
        except Exception:
            self.log_error("Python not found")
            return False

    def detect_node(self) -> bool:
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = result.stdout.strip()
            self.config["node"] = version
            self.log_info(f"Node: {version}")
            return True
        except Exception:
            self.log_warning("Node.js not found (frontend needs it; backend OK without)")
            return False

    def detect_git(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = result.stdout.strip()
            self.config["git"] = version
            self.log_info(f"Git: {version}")
            return True
        except Exception:
            self.log_error("Git not found")
            return False

    # ─────────────────────────────────────
    # Config files
    # ─────────────────────────────────────
    def setup_env_files(self) -> bool:
        self.log_info("Setting up local .env files...")
        try:
            frontend_env = (
                "NEXT_PUBLIC_API_BASE=http://localhost:8000\n"
                "NEXT_PUBLIC_BACKEND_URL=http://localhost:8000\n"
                "DATABASE_URL=sqlite:///./aura.db\n"
                "NODE_ENV=development\n"
            )
            with open("frontend/.env.local.dev", "w") as f:
                f.write(frontend_env)
            self.log_info("frontend/.env.local.dev created")

            backend_env = (
                "DATABASE_URL=sqlite:///./aura.db\n"
                "JWT_SECRET=dev-secret-aura-localhost-auto\n"
                "BRIDGE_SECRET=dev-secret-bridge-localhost-auto\n"
                "QWEN_URL=http://localhost:8000/api/ai\n"
            )
            with open("backend/.env.local", "w") as f:
                f.write(backend_env)
            self.log_info("backend/.env.local created")

            ame_env = (
                "DATABASE_URL=sqlite:///./aura.db\n"
                "JWT_SECRET=dev-secret-aura-localhost-auto\n"
                "BRIDGE_SECRET=dev-secret-bridge-localhost-auto\n"
                "FRONTEND_URL=http://localhost:3000\n"
            )
            with open("ame_backend/.env.local", "w") as f:
                f.write(ame_env)
            self.log_info("ame_backend/.env.local created")
            return True
        except Exception as e:
            self.log_error(f"Failed to create .env files: {e}")
            return False

    # ─────────────────────────────────────
    # Dependencies
    # ─────────────────────────────────────
    def install_python_deps(self) -> bool:
        self.log_info("Installing Python dependencies...")
        deps = {
            "backend": "backend/requirements.txt",
            "ame_backend": "ame_backend/requirements.txt",
        }
        for name, req_file in deps.items():
            if not os.path.exists(req_file):
                self.log_warning(f"{req_file} not found, skipping")
                continue
            try:
                self.log_info(f"Installing {name} deps...")
                result = subprocess.run(
                    ["pip", "install", "-r", req_file],
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if result.returncode == 0:
                    self.log_info(f"{name} deps installed")
                else:
                    # Do not abort: deps are usually already present; report and continue.
                    self.log_warning(
                        f"{name} pip install exited {result.returncode}; "
                        "continuing (deps may already be satisfied)"
                    )
            except Exception as e:
                self.log_error(f"Failed to install {name} deps: {e}")
                return False
        return True

    def install_node_deps(self) -> bool:
        if not self.detect_node():
            self.log_warning("Node not found, skipping frontend deps check")
            return True
        self.log_info("Checking frontend dependencies...")
        try:
            result = subprocess.run(
                ["npm", "list", "next", "--depth=0"],
                capture_output=True,
                text=True,
                cwd="frontend",
                timeout=15,
            )
            out = result.stdout
            if "next@" in out:
                version = out.split("next@")[1].split(" ")[0].strip()
                self.log_info(f"Next.js: {version} (installed)")
                try:
                    major = int(version.split(".")[0])
                except Exception:
                    major = 0
                if major >= 13:
                    self.log_info("Next.js 13+: App Router supported")
                else:
                    self.log_warning(
                        f"Next.js {major}: legacy (pages/ only). "
                        "Local frontend needs Next 13+; use Vercel for now."
                    )
            else:
                self.log_warning("Next.js not detected")
        except Exception as e:
            self.log_warning(f"Could not detect Next.js: {e}")
        return True

    # ─────────────────────────────────────
    # Services
    # ─────────────────────────────────────
    def start_backend(self) -> bool:
        self.log_info("Starting backend (localhost:8000)...")
        try:
            self.services["backend"] = subprocess.Popen(
                ["python", "-m", "ame_backend.src.main"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.log_info(f"Backend started (PID: {self.services['backend'].pid})")
            return True
        except Exception as e:
            self.log_error(f"Failed to start backend: {e}")
            return False

    def wait_for_service(self, url: str, timeout: int = 30) -> bool:
        import urllib.request

        start = time.time()
        while time.time() - start < timeout:
            try:
                response = urllib.request.urlopen(url, timeout=2)
                if response.status == 200:
                    return True
            except Exception:
                time.sleep(1)
        return False

    def verify_backend(self) -> bool:
        self.log_info("Verifying backend health...")
        if not self.wait_for_service("http://localhost:8000/health"):
            self.log_error("Backend health check timed out")
            return False
        try:
            import urllib.request

            response = urllib.request.urlopen("http://localhost:8000/health", timeout=5)
            return response.status == 200
        except Exception as e:
            self.log_error(f"Backend health check failed: {e}")
            return False

    # ─────────────────────────────────────
    # Summary
    # ─────────────────────────────────────
    def print_summary(self) -> None:
        print("\n" + "=" * 60)
        print("AURA AUTONOMOUS SETUP COMPLETE")
        print("=" * 60)
        print("\nSystem Configuration:")
        for key, value in self.config.items():
            print(f"  {key.upper()}: {value}")
        print("\nAccess URLs:")
        print("  Backend (Local):  http://localhost:8000")
        print(f"  Backend (WiFi):   http://{self.local_ip}:8000")
        print("  Health Check:     http://localhost:8000/health")
        print("\nNotes:")
        print("  - Frontend requires Next.js 13+ for local dev (installed: 9.3.3).")
        print("  - Vercel stays live: https://aura-web-chi-seven.vercel.app")
        print("  - Backend is ready at localhost:8000")
        print("\nActive Services:")
        for name, process in self.services.items():
            status = "Running" if process and process.poll() is None else "Stopped"
            pid = process.pid if process else "N/A"
            print(f"  {name}: {status} (PID: {pid})")
        print("\n" + "=" * 60)

    # ─────────────────────────────────────
    # Main
    # ─────────────────────────────────────
    def run_full_setup(self) -> bool:
        print("\n" + "=" * 60)
        print("AURA AUTONOMOUS CONFIG AGENT")
        print("=" * 60 + "\n")

        print("PHASE 1: Environment Detection")
        print("-" * 60)
        self.detect_os()
        self.detect_python()
        self.detect_node()
        self.detect_git()

        print("\nPHASE 2: Environment Setup")
        print("-" * 60)
        if not self.setup_env_files():
            self.log_error("Environment setup failed")
            return False

        print("\nPHASE 3: Dependencies Installation")
        print("-" * 60)
        self.install_python_deps()
        self.install_node_deps()

        print("\nPHASE 4: Starting Services")
        print("-" * 60)
        if not self.start_backend():
            self.log_error("Backend startup failed")
            return False

        time.sleep(5)
        if not self.verify_backend():
            self.log_error("Backend verification failed")
            return False

        self.print_summary()
        return True


if __name__ == "__main__":
    agent = AuraConfigAgent()
    success = agent.run_full_setup()
    if success:
        print("\nSetup complete. Press Ctrl+C to stop the backend.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            for name, process in agent.services.items():
                if process and process.poll() is None:
                    process.terminate()
                    print(f"  {name} stopped")
    else:
        print("\nSetup failed. Check errors above.")
        sys.exit(1)
