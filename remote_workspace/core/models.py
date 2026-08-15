from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal
import uuid


AuthType = Literal["password", "key"]


@dataclass
class ConnectionProfile:
    id: str
    name: str
    host: str
    port: int = 22
    username: str = ""
    auth_type: AuthType = "password"
    key_path: str = ""
    save_password: bool = False
    trust_new_hosts: bool = False
    local_path: str = ""
    remote_path: str = "."

    @classmethod
    def new(cls) -> "ConnectionProfile":
        return cls(
            id=str(uuid.uuid4()),
            name="New connection",
            host="",
            port=22,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "ConnectionProfile":
        return cls(
            id=value["id"],
            name=value.get("name", "Connection"),
            host=value.get("host", ""),
            port=int(value.get("port", 22)),
            username=value.get("username", ""),
            auth_type=value.get("auth_type", "password"),
            key_path=value.get("key_path", ""),
            save_password=bool(value.get("save_password", False)),
            trust_new_hosts=bool(value.get("trust_new_hosts", False)),
            local_path=value.get("local_path", ""),
            remote_path=value.get("remote_path", "."),
        )
