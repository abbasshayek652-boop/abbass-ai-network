from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Awaitable, Callable


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class Depends:  # noqa: D401 - simple marker
    def __init__(self, dependency: Callable[..., Any]) -> None:
        self.dependency = dependency


def Header(default: Any = None) -> Any:
    return default


class Request:
    def __init__(self) -> None:
        self.state = SimpleNamespace()
        self.client = SimpleNamespace(host="")


class Response:
    def __init__(self, content: Any = None, media_type: str | None = None) -> None:
        self.content = content
        self.media_type = media_type


class FastAPI:
    def __init__(self, **kwargs: Any) -> None:
        self.state = SimpleNamespace()
        self._startup: list[Callable[[], Awaitable[None] | None]] = []
        self._shutdown: list[Callable[[], Awaitable[None] | None]] = []

    def add_middleware(self, *args: Any, **kwargs: Any) -> None:
        return None

    def mount(self, *args: Any, **kwargs: Any) -> None:
        return None

    def include_router(self, router: Any) -> None:
        return None

    def on_event(self, event: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            if event == "startup":
                self._startup.append(func)
            elif event == "shutdown":
                self._shutdown.append(func)
            return func

        return decorator

    def exception_handler(self, exc_class: type) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator

    def get(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator

    def post(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator


class APIRouter:
    def __init__(self) -> None:
        self.routes: list[Callable[..., Any]] = []

    def get(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(func)
            return func

        return decorator

    def post(self, path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(func)
            return func

        return decorator

    def websocket(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes.append(func)
            return func

        return decorator


class WebSocketDisconnect(Exception):
    pass


class WebSocket:
    pass


class status:
    HTTP_401_UNAUTHORIZED = 401
    HTTP_403_FORBIDDEN = 403
    HTTP_404_NOT_FOUND = 404
    HTTP_423_LOCKED = 423
    HTTP_429_TOO_MANY_REQUESTS = 429
    HTTP_500_INTERNAL_SERVER_ERROR = 500
    HTTP_503_SERVICE_UNAVAILABLE = 503
