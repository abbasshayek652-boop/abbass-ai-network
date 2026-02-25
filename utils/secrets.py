from __future__ import annotations

import logging
from typing import Optional

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover
    Fernet = None  # type: ignore


def _build_fernet(key: str | None):
    if Fernet is None or not key:
        return None
    try:
        Fernet(key)
    except Exception as exc:  # pragma: no cover
        LOGGER.warning("Invalid fernet key provided: %s", exc)
        return None
    return Fernet(key)


def decrypt(secret: str | None, key: str | None) -> Optional[str]:
    if secret is None:
        return None
    fernet = _build_fernet(key)
    if fernet is None:
        return secret
    try:
        return fernet.decrypt(secret.encode()).decode()
    except Exception as exc:  # pragma: no cover
        LOGGER.warning("Failed to decrypt secret: %s", exc)
        return secret


def encrypt(secret: str, key: str | None) -> str:
    fernet = _build_fernet(key)
    if fernet is None:
        return secret
    return fernet.encrypt(secret.encode()).decode()

