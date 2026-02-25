from __future__ import annotations

import datetime as dt
import secrets
from dataclasses import dataclass
from typing import Callable, Literal

from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel

from ai.settings import settings

ALGORITHM = "HS256"
Role = Literal["viewer", "operator", "admin"]
ROLE_LEVEL: dict[Role, int] = {"viewer": 0, "operator": 1, "admin": 2}


class TokenPayload(BaseModel):
    sub: str
    role: Role
    exp: int


@dataclass(slots=True)
class AuthContext:
    user_id: str
    role: Role
    via_api_key: bool = False


def issue_jwt(sub: str, role: Role, ttl_minutes: int = 60) -> str:
    if not settings.jwt_secret:
        raise RuntimeError("JWT secret not configured")
    now = dt.datetime.utcnow()
    payload = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(minutes=ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def _decode(token: str) -> TokenPayload:
    if not settings.jwt_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWT disabled")
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    return TokenPayload(**data)


def decode_token(token: str) -> TokenPayload:
    return _decode(token)


def require(role: Role) -> Callable[[Request, str | None, str | None], AuthContext]:
    required_level = ROLE_LEVEL[role]

    async def dependency(
        request: Request,
        authorization: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ) -> AuthContext:
        if x_api_key is not None:
            if settings.api_key and secrets.compare_digest(x_api_key, settings.api_key):
                request.state.user_id = "api-key"
                request.state.user_role = "admin"
                return AuthContext(user_id="api-key", role="admin", via_api_key=True)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1]
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization required")
        payload = _decode(token)
        if ROLE_LEVEL[payload.role] < required_level:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        request.state.user_id = payload.sub
        request.state.user_role = payload.role
        return AuthContext(user_id=payload.sub, role=payload.role)

    return dependency


async def get_viewer(ctx: AuthContext = Depends(require("viewer"))) -> AuthContext:
    return ctx


async def get_operator(ctx: AuthContext = Depends(require("operator"))) -> AuthContext:
    return ctx


async def get_admin(ctx: AuthContext = Depends(require("admin"))) -> AuthContext:
    return ctx
