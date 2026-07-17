"""Auth helpers for admin API.

- JWT validation
- RBAC (role-based access control)
- Audit logging
- Rate limiting
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from time import time
from typing import Dict, List, Optional

import jwt
from fastapi import Depends, Header, HTTPException

try:
    from dotenv import load_dotenv

    for _env_path in ("backend/.env.local", ".env.local"):
        load_dotenv(_env_path)
except Exception as _e:  # pragma: no cover - optional in some environments
    pass

# ─────────────────────────────────────
# ROLES & PERMISSIONS
# ─────────────────────────────────────


class Role(str, Enum):
    ADMIN = "admin"
    VIEWER = "viewer"


ROLE_PERMISSIONS = {
    Role.ADMIN: [
        "servers:read",
        "servers:write",
        "servers:switch",
        "servers:sync",
        "servers:delete",
        "audit:read",
    ],
    Role.VIEWER: [
        "servers:read",
        "audit:read",
    ],
}


# ─────────────────────────────────────
# JWT HELPERS
# ─────────────────────────────────────


class AuthManager:
    def __init__(self) -> None:
        self.algorithm = "HS256"
        self.expiration_hours = 24

    @property
    def secret_key(self) -> str:
        # Read at call time so the value reflects the environment active when
        # the request is handled (dotenv may load after import in some setups).
        return os.getenv("JWT_SECRET_ADMIN", "dev-secret-admin-change-me")

    def create_token(
        self, user_id: str, role: Role, metadata: Optional[Dict] = None
    ) -> str:
        now = datetime.utcnow()
        payload = {
            "user_id": user_id,
            "role": role.value,
            # issued 60s in the past to tolerate any clock skew between
            # the signer and the verifier.
            "iat": int((now - timedelta(seconds=60)).timestamp()),
            "exp": int((now + timedelta(hours=self.expiration_hours)).timestamp()),
            "metadata": metadata or {},
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Dict:
        try:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                # iat is intentionally not verified: the signer and verifier may
                # run on hosts with a small clock skew. exp is still enforced.
                options={"verify_aud": False, "verify_iat": False},
                leeway=10,
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def has_permission(self, role: Role, permission: str) -> bool:
        return permission in ROLE_PERMISSIONS.get(role, [])


auth_manager = AuthManager()


# ─────────────────────────────────────
# DEPENDENCY INJECTION
# ─────────────────────────────────────


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    return auth_manager.verify_token(token)


async def require_permission(permission: str):
    async def check_permission(
        current_user: Dict = Depends(get_current_user),
    ) -> Dict:
        role = Role(current_user.get("role"))
        if not auth_manager.has_permission(role, permission):
            raise HTTPException(
                status_code=403, detail=f"Permission denied: {permission}"
            )
        return current_user

    return check_permission


# ─────────────────────────────────────
# AUDIT LOGGING
# ─────────────────────────────────────


class AuditLogger:
    def __init__(self, log_file: str = "admin_audit.log") -> None:
        self.log_file = log_file

    def log_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        details: Optional[Dict] = None,
        status: str = "success",
    ) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "status": status,
            "details": details or {},
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"[AUDIT] {entry['timestamp']} | {user_id} | {action} {resource} | {status}")

    def read_logs(self, limit: int = 100) -> List[Dict]:
        logs: List[Dict] = []
        try:
            with open(self.log_file, "r") as f:
                for line in f.readlines()[-limit:]:
                    logs.append(json.loads(line))
        except FileNotFoundError:
            pass
        return logs


audit_logger = AuditLogger()


# ─────────────────────────────────────
# RATE LIMITING
# ─────────────────────────────────────


class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, user_id: str) -> bool:
        now = time()
        self.requests[user_id] = [
            t for t in self.requests[user_id] if now - t < self.window_seconds
        ]
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        self.requests[user_id].append(now)
        return True


rate_limiter = RateLimiter(max_requests=10, window_seconds=60)
