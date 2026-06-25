"""
Profile memory loader for AME backend.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class ProfileMemory:
    def __init__(
        self, profile_path: str | Path = "ame-backend/src/automation/golden_profile.json"
    ) -> None:
        self._path = Path(profile_path)
        self._profile: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        if self._path.exists():
            self._profile = json.loads(self._path.read_text(encoding="utf-8"))
        else:
            self._profile = {}

    @property
    def profile(self) -> Dict[str, Any]:
        return self._profile

    def get_section(self, section: str) -> Dict[str, Any]:
        return self._profile.get(section, {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._profile.get(key, default)
