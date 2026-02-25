from __future__ import annotations

import json
from typing import Any, Callable


class RequestException(RuntimeError):
    pass


class Response:
    def __init__(self, status_code: int = 200, data: Any | None = None, text: str | None = None) -> None:
        self.status_code = status_code
        self._data = data
        self.text = text or (json.dumps(data) if data is not None else "")

    def json(self) -> Any:
        if self._data is not None:
            return self._data
        if not self.text:
            return None
        return json.loads(self.text)


def _not_implemented(*_args: Any, **_kwargs: Any) -> Response:
    raise RequestException("Network access disabled in this environment")


get: Callable[..., Response] = _not_implemented
post: Callable[..., Response] = _not_implemented
put: Callable[..., Response] = _not_implemented
