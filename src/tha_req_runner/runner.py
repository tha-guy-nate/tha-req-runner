from __future__ import annotations

import threading
from collections.abc import Collection
from typing import Any, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_DEFAULT_RETRIES = 3
_DEFAULT_BACKOFF = 0.5
_DEFAULT_STATUS_FORCELIST = (500, 502, 503, 504)
_DEFAULT_TIMEOUT = 30


class ThaReq:
    def __init__(self) -> None:
        self._local = threading.local()

    def get_session(
        self,
        *,
        status_forcelist: tuple[int, ...] = _DEFAULT_STATUS_FORCELIST,
        allowed_methods: Collection[str] | None = None,  # None → urllib3 safe-method default; POST excluded
        headers: dict[str, str] | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> requests.Session:
        # config applies only on first call per thread; subsequent calls return the cached session
        if not hasattr(self._local, "session"):
            session = requests.Session()
            retry = Retry(
                total=_DEFAULT_RETRIES,
                backoff_factor=_DEFAULT_BACKOFF,
                status_forcelist=status_forcelist,
                allowed_methods=allowed_methods,
            )
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            if headers:
                session.headers.update(headers)
            self._local.session = session
            self._local.timeout = timeout
        return self._local.session  # type: ignore[no-any-return]

    def reset_session(self) -> None:
        """Discard the current thread's session so the next get_session() call creates a fresh one."""
        if hasattr(self._local, "session"):
            self._local.session.close()
            del self._local.session
        if hasattr(self._local, "timeout"):
            del self._local.timeout

    def close_session(self) -> None:
        """Close and discard the current thread's session. Alias for reset_session with explicit intent."""
        self.reset_session()

    @property
    def timeout(self) -> float:
        return getattr(self._local, "timeout", _DEFAULT_TIMEOUT)  # type: ignore[no-any-return]

    @staticmethod
    def parse_response(result: requests.Response | Exception) -> dict[str, Any]:
        if isinstance(result, Exception):
            raw = getattr(result, "response", None)
            if not isinstance(raw, requests.Response):
                raw = None
            return {
                "status": raw.status_code if raw is not None else None,
                "data": None,
                "message": str(result),
                "raw_response": raw,
            }
        try:
            data: Any = result.json()
        except Exception:
            data = None
        return {
            "status": result.status_code,
            "data": data,
            "message": None,
            "raw_response": result,
        }

    def safe_call(
        self,
        fn: Callable[..., requests.Response],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        kwargs.setdefault("timeout", self.timeout)
        try:
            return self.parse_response(fn(*args, **kwargs))
        except Exception as exc:
            return self.parse_response(exc)
