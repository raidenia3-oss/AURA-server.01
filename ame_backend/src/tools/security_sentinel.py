"""
Centinela de Ciberseguridad — Inteligencia defensiva proactiva de AURA.

Escanea fuentes públicas de vulnerabilidades y logs locales para detectar
amenazas reales. Genera micro-reportes estructurados por severidad:

  - CRITICAL: vulnerabilidades explotadas activamente (CISA KEV).
  - HIGH: dependencias desactualizadas en componentes críticos del backend.
  - MEDIUM: patrones de ataque en logs locales.
  - LOW/INFO: hallazgos informativos.

Diseño resiliente: si una fuente no es alcanzable, el escaneo continúa
con las demás y registra el fallo sin detener el ciclo.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from ame_backend.src.tools import browser as _browser
except Exception:  # pragma: no cover
    _browser = None  # type: ignore

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

logger = logging.getLogger(__name__)

_CISA_KEV_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/"
    "known_exploited_vulnerabilities.json"
)

_THREAT_PATTERNS = [
    ("sql_injection_attempt", r"(?i)(union\s+select|select\s+.*\s+from|drop\s+table|insert\s+into|--\s*$)"),
    ("xss_attempt", r"(?i)(<script|javascript:|onerror=|onload=|alert\()"),
    ("path_traversal", r"(?i)(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e\\)"),
    ("command_injection", r"(?i)(;|\||`|\$\().*(rm|curl|wget|nc|ncat|bash|sh\s)"),
    ("auth_bruteforce", r"(?i)(failed\s+login|authentication\s+failure|invalid\s+password)"),
]

_BACKEND_COMPONENTS = {
    "fastapi", "uvicorn", "starlette", "sqlalchemy", "requests",
    "pyjwt", "python-multipart", "python-dotenv", "httpx",
    "discord.py", "psycopg2-binary", "psycopg2", "pymongo",
    "cryptography", "bcrypt", "passlib", "jwt",
}

_CRITICAL_PKGS = {
    "fastapi", "starlette", "sqlalchemy", "requests", "cryptography",
    "bcrypt", "pyjwt", "jwt", "python-multipart",
}


class SecurityThreat:
    """Micro-reporte de amenaza de seguridad."""

    def __init__(
        self,
        category: str,
        severity: str,
        source: str,
        detail: str,
        recommendation: str = "",
    ) -> None:
        self.category = category
        self.severity = severity.upper()
        self.source = source
        self.detail = detail
        self.recommendation = recommendation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "source": self.source,
            "detail": self.detail,
            "recommendation": self.recommendation,
        }


class SecuritySentinel:
    """Módulo de inteligencia defensiva proactiva de AURA."""

    def __init__(self, project_root: Optional[str] = None) -> None:
        if project_root is None:
            project_root = str(Path(__file__).resolve().parents[3])
        self.project_root = project_root
        self._requirements_path = os.path.join(self.project_root, "requirements.txt")

    async def run_vulnerability_scan(self) -> Dict[str, Any]:
        """Ejecuta el escaneo completo de seguridad y devuelve el reporte."""
        threats: List[SecurityThreat] = []

        try:
            threats.extend(await self._check_cisa_kev())
        except Exception as exc:
            logger.error("Sentinel CISA KEV falló: %s", exc)

        try:
            threats.extend(await self._check_pypi_versions())
        except Exception as exc:
            logger.error("Sentinel PyPI versions falló: %s", exc)

        try:
            threats.extend(await self._scan_local_logs())
        except Exception as exc:
            logger.error("Sentinel log scan falló: %s", exc)

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        threats.sort(key=lambda t: (severity_order.get(t.severity, 5), t.category))

        critical_high = [t for t in threats if t.severity in ("CRITICAL", "HIGH")]
        return {
            "ok": True,
            "scan_time": __import__("datetime").datetime.now().isoformat(),
            "total_threats": len(threats),
            "critical_high_count": len(critical_high),
            "threats": [t.to_dict() for t in threats],
            "has_critical": any(t.severity == "CRITICAL" for t in threats),
        }

    async def _check_cisa_kev(self) -> List[SecurityThreat]:
        """Consulta el catálogo CISA KEV de vulnerabilidades explotadas."""
        threats: List[SecurityThreat] = []
        if httpx is None and _browser is None:
            return threats

        data = None
        try:
            if httpx is not None:
                async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                    resp = await client.get(_CISA_KEV_URL)
                    resp.raise_for_status()
                    data = resp.json()
            elif _browser is not None:
                text = await _browser.fetch_clean_text_async(
                    _CISA_KEV_URL, timeout=20.0, max_chars=50000
                )
                data = json.loads(text)
        except Exception as exc:
            logger.warning("No se pudo obtener CISA KEV: %s", exc)
            return threats

        vulns = data.get("vulnerabilities", []) if isinstance(data, dict) else []
        if not vulns:
            return threats

        keywords = [
            "fastapi", "uvicorn", "starlette", "sqlalchemy", "requests",
            "pyjwt", "jwt", "python-multipart", "python dotenv",
            "discord.py", "rocket.chat", "psycopg2", "pymongo",
            "python", "fast api",
        ]

        relevant: List[Dict[str, Any]] = []
        for v in vulns:
            product = (v.get("product", "") or "").lower()
            name = (v.get("vulnerabilityName", "") or "").lower()
            if any(k in product or k in name for k in keywords):
                relevant.append(v)
            if len(relevant) >= 20:
                break

        for v in relevant:
            cve_id = v.get("cveID", "")
            product = v.get("product", "N/A")
            name = v.get("vulnerabilityName", "Sin nombre")
            severity = v.get("severity", "HIGH")
            if severity not in ("CRITICAL", "HIGH", "MEDIUM"):
                severity = "HIGH"
            threats.append(SecurityThreat(
                category="cisa_kev",
                severity=severity,
                source="CISA Known Exploited Vulnerabilities",
                detail=f"{cve_id}: {name} (Producto: {product})",
                recommendation=(
                    f"Actualizar componente afectado inmediatamente. "
                    f"Ver detalle: https://nvd.nist.gov/vuln/detail/{cve_id}"
                ),
            ))
        return threats

    async def _check_pypi_versions(self) -> List[SecurityThreat]:
        """Compara versiones en requirements.txt con las últimas estables en PyPI."""
        threats: List[SecurityThreat] = []
        if not os.path.isfile(self._requirements_path):
            return threats
        try:
            raw = open(self._requirements_path, "r", encoding="utf-8").read()
        except Exception:
            return threats

        packages = re.findall(r"^([A-Za-z0-9_.-]+)(?:[=<>!~]+)([0-9.]+)", raw, re.MULTILINE)
        if not packages:
            return threats

        filtered = [(p, v) for p, v in packages if p.lower() in _BACKEND_COMPONENTS]
        if not filtered:
            return threats

        async def fetch_latest(package: str) -> Optional[str]:
            url = f"https://pypi.org/pypi/{package}/json"
            try:
                if httpx is not None:
                    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                        resp = await client.get(url)
                        if resp.status_code == 404:
                            return None
                        resp.raise_for_status()
                        return resp.json().get("info", {}).get("version")
                elif _browser is not None:
                    text = await _browser.fetch_clean_text_async(
                        url, timeout=15.0, max_chars=4000
                    )
                    data = json.loads(text)
                    return data.get("info", {}).get("version")
            except Exception:
                pass
            return None

        results = await asyncio.gather(
            *[fetch_latest(pkg) for pkg, _ in filtered], return_exceptions=True
        )
        for (pkg, pinned), latest in zip(filtered, results):
            if isinstance(latest, Exception) or latest is None:
                continue
            if latest > pinned:
                threats.append(SecurityThreat(
                    category="outdated_dependency",
                    severity="HIGH" if pkg.lower() in _CRITICAL_PKGS else "MEDIUM",
                    source="PyPI / requirements.txt",
                    detail=f"{pkg} desactualizado: instalado={pinned}, latest={latest}",
                    recommendation=f"Actualizar {pkg} a {latest} en requirements.txt y redesplegar.",
                ))
        return threats

    async def _scan_local_logs(self) -> List[SecurityThreat]:
        """Escanea logs locales en busca de patrones de ataque."""
        threats: List[SecurityThreat] = []
        log_files = [
            "auto_audit_debate.log",
            "rocket_bridge_test.log",
            "admin_audit.log",
            "audit.log",
        ]
        for name in log_files:
            path = os.path.join(self.project_root, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[-500:]
                for i, line in enumerate(lines):
                    for pattern_name, pattern in _THREAT_PATTERNS:
                        if re.search(pattern, line):
                            threats.append(SecurityThreat(
                                category="log_anomaly",
                                severity="MEDIUM",
                                source=f"Log local: {name}",
                                detail=(
                                    f"Patrón sospechoso '{pattern_name}' "
                                    f"en línea {i + 1}: {line.strip()[:220]}"
                                ),
                                recommendation=(
                                    "Verificar origen de la request y reforzar "
                                    "WAF/validación de entrada."
                                ),
                            ))
                            break
            except Exception:
                pass
        return threats
