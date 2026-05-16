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


class ThaReq:
    def __init__(self) -> None:
        self._local = threading.local()

    def get_session(
        self,
        *,
        status_forcelist: tuple[int, ...] = _DEFAULT_STATUS_FORCELIST,
        allowed_methods: Collection[str] | None = None,  # None → urllib3 safe-method default; POST excluded
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
            self._local.session = session
        return self._local.session  # type: ignore[no-any-return]

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
        try:
            return self.parse_response(fn(*args, **kwargs))
        except Exception as exc:
            return self.parse_response(exc)
