"""tha-req-runner: thread-safe HTTP requests with automatic retries and normalized responses."""

from .errors import ReqError
from .runner import ThaReq

__version__ = "0.3.0"
__all__ = ["ReqError", "ThaReq"]
