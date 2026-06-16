from __future__ import annotations

import threading
from collections.abc import Collection
from typing import Any, Callable, Literal, cast

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    import httpx

    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

_DEFAULT_RETRIES = 3
_DEFAULT_BACKOFF = 0.5
_DEFAULT_STATUS_FORCELIST = (500, 502, 503, 504)
_DEFAULT_TIMEOUT = 30


class ThaReq:
    def __init__(self, *, backend: Literal["requests", "httpx"] = "requests") -> None:
        if backend == "httpx" and not _HTTPX_AVAILABLE:
            raise ImportError("httpx is not installed. Run: pip install tha-req-runner[httpx]")
        self._local = threading.local()
        self._backend = backend

    def get_session(
        self,
        *,
        status_forcelist: tuple[int, ...] = _DEFAULT_STATUS_FORCELIST,  # requests only
        allowed_methods: Collection[str]
        | None = None,  # requests only; None → urllib3 safe-method default
        headers: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> Any:
        # config applies only on first call per thread; subsequent calls return the cached session
        if not hasattr(self._local, "session"):
            if self._backend == "requests":
                retry = Retry(
                    total=_DEFAULT_RETRIES,
                    backoff_factor=_DEFAULT_BACKOFF,
                    status_forcelist=status_forcelist,
                    allowed_methods=allowed_methods,
                )
                session: Any = requests.Session()
                adapter = HTTPAdapter(max_retries=retry)
                session.mount("https://", adapter)
                session.mount("http://", adapter)
                if headers:
                    session.headers.update(headers)
            else:
                transport = httpx.HTTPTransport(retries=_DEFAULT_RETRIES)
                session = httpx.Client(transport=transport, headers=headers or {})
            self._local.session = session
            self._local.timeout = timeout
        return self._local.session

    def reset_session(self) -> None:
        if hasattr(self._local, "session"):
            self._local.session.close()
            del self._local.session
        if hasattr(self._local, "timeout"):
            del self._local.timeout

    def close_session(self) -> None:
        self.reset_session()

    @property
    def timeout(self) -> float:
        return cast(float, getattr(self._local, "timeout", _DEFAULT_TIMEOUT))

    @staticmethod
    def parse_response(result: Any) -> dict[str, Any]:
        def _try_json(obj: Any) -> Any:
            try:
                return obj.json()
            except Exception:
                return None

        if isinstance(result, Exception):
            raw = getattr(result, "response", None)
            valid_types = (
                (requests.Response, httpx.Response) if _HTTPX_AVAILABLE else (requests.Response,)
            )
            if not isinstance(raw, valid_types):
                raw = None
            return {
                "status": "error",
                "code": raw.status_code if raw is not None else None,
                "data": _try_json(raw) if raw is not None else None,
                "message": str(result),
                "raw_response": raw,
            }
        return {
            "status": None,
            "code": result.status_code,
            "data": _try_json(result),
            "message": None,
            "raw_response": result,
        }

    def safe_call(
        self,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs.setdefault("timeout", self.timeout)
        try:
            resp = fn(*args, **kwargs)
            resp.raise_for_status()
            return self.parse_response(resp)
        except Exception as exc:
            return self.parse_response(exc)
