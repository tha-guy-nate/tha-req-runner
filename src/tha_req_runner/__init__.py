"""tha-req-runner: thread-safe HTTP requests with automatic retries and normalized responses."""

from importlib.metadata import version

from .errors import ReqError
from .runner import ThaReq

__version__ = version("tha-req-runner")
__all__ = ["ReqError", "ThaReq"]
