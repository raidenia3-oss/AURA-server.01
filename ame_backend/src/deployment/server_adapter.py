"""Multi-server deployment adapter framework for AURA/AME.

Abstraction over multiple hosting targets (Local, Vercel, Railway, AWS) so the
system can register servers, check their health, deploy, sync the database and
switch the active target without downtime.

External CLIs (vercel, railway) and cloud SDKs are used lazily/optionally; when
a target's credentials are missing the adapter reports it cleanly instead of
raising, so the framework is safe to import and run with only the Local target.
"""

from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

try:  # optional; only needed for real health checks
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore


class ServerType(str, Enum):
    LOCAL = "local"
    VERCEL = "vercel"
    RAILWAY = "railway"
    AWS = "aws"


class ServerAdapter(ABC):
    """Base adapter for any hosting target."""

    def __init__(self) -> None:
        self.credentials: Dict[str, str] = {}
        self.url: str = ""

    @abstractmethod
    def connect(self, credentials: Dict[str, str]) -> bool:
        """Validate/store credentials. Return True if the target is usable."""

    @abstractmethod
    def deploy(self, code_path: str) -> Dict[str, Any]:
        """Deploy code. Return {'ok': bool, ...}."""

    @abstractmethod
    def get_url(self) -> str:
        """Public URL of the target (best-effort)."""

    def health_check(self) -> Dict[str, Any]:
        """Default HTTP health check against ``<url>/health``."""
        url = self.get_url()
        if not url:
            return {"ok": False, "error": "No URL for target"}
        if requests is None:
            return {"ok": False, "error": "requests not installed"}
        for path in ("/health", "/api/health"):
            try:
                resp = requests.get(url.rstrip("/") + path, timeout=5)
                if resp.status_code == 200:
                    return {"ok": True, "status": 200, "url": url + path}
            except Exception:
                continue
        return {"ok": False, "error": "health check failed", "url": url}

    def sync_database(self, db_url: str) -> Dict[str, Any]:
        """Set DATABASE_URL on the target. Overridden per adapter."""
        return {"ok": False, "error": "sync not supported for this target"}


class LocalAdapter(ServerAdapter):
    def connect(self, credentials: Dict[str, str]) -> bool:
        self.credentials = credentials or {}
        self.url = credentials.get("url", "http://localhost:8000")
        return True

    def deploy(self, code_path: str) -> Dict[str, Any]:
        # Local "deploy" = (re)start is out of scope here; report guidance.
        return {
            "ok": True,
            "message": "Local target: start with 'python -m ame_backend.src.main'",
        }

    def get_url(self) -> str:
        return self.url or "http://localhost:8000"

    def sync_database(self, db_url: str) -> Dict[str, Any]:
        # Local uses its own .env; nothing remote to set.
        return {"ok": True, "message": "Local uses .env.local"}


class VercelAdapter(ServerAdapter):
    def connect(self, credentials: Dict[str, str]) -> bool:
        self.credentials = credentials or {}
        self.token = self.credentials.get("VERCEL_TOKEN")
        self.project = self.credentials.get("VERCEL_PROJECT_ID")
        if not self.token or not self.project:
            return False
        if requests is None:
            return True  # can't verify online, but creds present
        try:
            resp = requests.get(
                f"https://api.vercel.com/v9/projects/{self.project}",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=8,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def deploy(self, code_path: str) -> Dict[str, Any]:
        if not self.credentials.get("VERCEL_TOKEN"):
            return {"ok": False, "error": "VERCEL_TOKEN missing"}
        try:
            subprocess.run(
                ["vercel", "deploy", "--prod", "--token", self.credentials["VERCEL_TOKEN"]],
                cwd=code_path,
                check=True,
            )
            return {"ok": True, "url": self.get_url()}
        except FileNotFoundError:
            return {"ok": False, "error": "vercel CLI not installed"}
        except subprocess.CalledProcessError as e:
            return {"ok": False, "error": f"vercel deploy failed: {e}"}

    def sync_database(self, db_url: str) -> Dict[str, Any]:
        token = self.credentials.get("VERCEL_TOKEN")
        if not token:
            return {"ok": False, "error": "VERCEL_TOKEN missing"}
        try:
            subprocess.run(
                ["vercel", "env", "add", "DATABASE_URL", "production", "--token", token],
                input=db_url,
                text=True,
                check=True,
            )
            return {"ok": True}
        except FileNotFoundError:
            return {"ok": False, "error": "vercel CLI not installed"}
        except subprocess.CalledProcessError as e:
            return {"ok": False, "error": str(e)}

    def get_url(self) -> str:
        if self.url:
            return self.url
        token = self.credentials.get("VERCEL_TOKEN")
        project = self.credentials.get("VERCEL_PROJECT_ID")
        if requests is not None and token and project:
            try:
                resp = requests.get(
                    f"https://api.vercel.com/v9/projects/{project}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=8,
                )
                if resp.status_code == 200:
                    name = resp.json().get("name")
                    if name:
                        self.url = f"https://{name}.vercel.app"
                        return self.url
            except Exception:
                pass
        return self.credentials.get("url", "")


class RailwayAdapter(ServerAdapter):
    def connect(self, credentials: Dict[str, str]) -> bool:
        self.credentials = credentials or {}
        self.token = self.credentials.get("RAILWAY_TOKEN")
        return bool(self.token)

    def deploy(self, code_path: str) -> Dict[str, Any]:
        token = self.credentials.get("RAILWAY_TOKEN")
        if not token:
            return {"ok": False, "error": "RAILWAY_TOKEN missing"}
        try:
            subprocess.run(
                ["railway", "up", "--detach"],
                cwd=code_path,
                env={**os.environ, "RAILWAY_TOKEN": token},
                check=True,
            )
            return {"ok": True, "message": "railway up queued; verify deployment list"}
        except FileNotFoundError:
            return {"ok": False, "error": "railway CLI not installed"}
        except subprocess.CalledProcessError as e:
            return {"ok": False, "error": f"railway up failed: {e}"}

    def sync_database(self, db_url: str) -> Dict[str, Any]:
        token = self.credentials.get("RAILWAY_TOKEN")
        if not token:
            return {"ok": False, "error": "RAILWAY_TOKEN missing"}
        try:
            subprocess.run(
                ["railway", "variable", "set", f"DATABASE_URL={db_url}"],
                env={**os.environ, "RAILWAY_TOKEN": token},
                check=True,
            )
            return {"ok": True}
        except FileNotFoundError:
            return {"ok": False, "error": "railway CLI not installed"}
        except subprocess.CalledProcessError as e:
            return {"ok": False, "error": str(e)}

    def get_url(self) -> str:
        return self.url or self.credentials.get("url", "")


class AWSAdapter(ServerAdapter):
    """Placeholder AWS adapter. Deploy/sync require boto3 + account setup."""

    def connect(self, credentials: Dict[str, str]) -> bool:
        self.credentials = credentials or {}
        return bool(
            self.credentials.get("AWS_ACCESS_KEY_ID")
            and self.credentials.get("AWS_SECRET_ACCESS_KEY")
        )

    def deploy(self, code_path: str) -> Dict[str, Any]:
        return {"ok": False, "error": "AWS deploy not implemented (needs boto3 + target)"}

    def get_url(self) -> str:
        return self.url or self.credentials.get("url", "")


class ServerManager:
    """Registers, health-checks and switches between hosting targets."""

    def __init__(self) -> None:
        self.adapters: Dict[ServerType, ServerAdapter] = {
            ServerType.LOCAL: LocalAdapter(),
            ServerType.VERCEL: VercelAdapter(),
            ServerType.RAILWAY: RailwayAdapter(),
            ServerType.AWS: AWSAdapter(),
        }
        self.registered: Dict[ServerType, bool] = {ServerType.LOCAL: True}
        self.adapters[ServerType.LOCAL].connect({})
        self.active: ServerType = ServerType.LOCAL

    def register_server(self, server_type: ServerType, credentials: Dict[str, str]) -> bool:
        adapter = self.adapters.get(server_type)
        if not adapter:
            return False
        ok = adapter.connect(credentials or {})
        self.registered[server_type] = ok
        return ok

    def list_servers(self) -> Dict[str, Any]:
        out = []
        for st, adapter in self.adapters.items():
            out.append(
                {
                    "type": st.value,
                    "registered": self.registered.get(st, False),
                    "active": st == self.active,
                    "url": adapter.get_url(),
                }
            )
        return {"active": self.active.value, "servers": out}

    def switch_server(self, target: ServerType) -> Dict[str, Any]:
        if not self.registered.get(target):
            return {"ok": False, "error": f"{target.value} not registered"}
        health = self.adapters[target].health_check()
        if not health.get("ok"):
            return {"ok": False, "error": "target unhealthy", "health": health}
        self.active = target
        return {"ok": True, "active": target.value, "url": self.adapters[target].get_url()}

    def deploy_to(self, target: ServerType, code_path: str) -> Dict[str, Any]:
        adapter = self.adapters.get(target)
        if not adapter or not self.registered.get(target):
            return {"ok": False, "error": f"{target.value} not registered"}
        return adapter.deploy(code_path)

    def sync_all(self, db_url: str) -> Dict[str, Any]:
        results = {}
        for st, adapter in self.adapters.items():
            if self.registered.get(st):
                results[st.value] = adapter.sync_database(db_url)
        return {"ok": True, "results": results}


# Module-level singleton used by the API router.
manager = ServerManager()
