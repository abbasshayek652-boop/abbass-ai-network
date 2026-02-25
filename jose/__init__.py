from __future__ import annotations

import base64
import json


class JWTError(Exception):
    pass


class _JWT:
    def encode(self, payload: dict[str, object], secret: str, algorithm: str = "HS256") -> str:
        data = json.dumps(payload).encode()
        return base64.urlsafe_b64encode(data).decode()

    def decode(self, token: str, secret: str, algorithms: list[str] | None = None) -> dict[str, object]:
        try:
            data = base64.urlsafe_b64decode(token.encode())
            return json.loads(data.decode())
        except Exception as exc:  # noqa: BLE001
            raise JWTError("Invalid token") from exc


jwt = _JWT()
