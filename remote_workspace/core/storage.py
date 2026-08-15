from __future__ import annotations

import json
from pathlib import Path

import keyring
from PySide6.QtCore import QStandardPaths

from .models import ConnectionProfile


SERVICE_NAME = "RemoteWorkspace"


class ConnectionStore:
    def __init__(self):
        app_dir = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        app_dir.mkdir(parents=True, exist_ok=True)
        self.app_dir = app_dir
        self.connections_file = app_dir / "connections.json"
        self.known_hosts_file = app_dir / "known_hosts"

    def load(self) -> list[ConnectionProfile]:
        if not self.connections_file.exists():
            return []
        try:
            raw = json.loads(self.connections_file.read_text(encoding="utf-8"))
            return [ConnectionProfile.from_dict(item) for item in raw]
        except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
            return []

    def save(self, profiles: list[ConnectionProfile]) -> None:
        payload = [profile.to_dict() for profile in profiles]
        self.connections_file.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    def set_password(self, profile_id: str, password: str) -> None:
        keyring.set_password(SERVICE_NAME, profile_id, password)

    def get_password(self, profile_id: str) -> str | None:
        try:
            return keyring.get_password(SERVICE_NAME, profile_id)
        except Exception:
            return None

    def delete_password(self, profile_id: str) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, profile_id)
        except keyring.errors.PasswordDeleteError:
            pass
        except Exception:
            pass
