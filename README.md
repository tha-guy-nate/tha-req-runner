# tha-req-runner

[![CI](https://github.com/tha-guy-nate/tha-req-runner/actions/workflows/ci.yml/badge.svg)](https://github.com/tha-guy-nate/tha-req-runner/actions/workflows/ci.yml)

A small Python library that provides a thread-safe HTTP session with automatic retries and a normalized response parser. Supports both `requests` (default) and `httpx` backends. Intended as the HTTP transport layer for other `tha-*` runners.

## Install

```bash
pip install tha-req-runner           # requests backend (default)
pip install tha-req-runner[httpx]    # adds httpx backend support
```

## Quick start

```python
from tha_req_runner import ThaReq

# requests backend (default)
req = ThaReq()
session = req.get_session()

# httpx backend
req = ThaReq(backend="httpx")
client = req.get_session()

# safe_call wraps the try/except for you — same API regardless of backend
result = req.safe_call(session.get, "https://api.example.com/students", params={"limit": 100})
# {"status": 200, "data": [...], "message": None, "raw_response": <Response>}

# network errors return the same shape — no try/except needed
result = req.safe_call(session.get, "https://unreachable.example.com")
# {"status": None, "data": None, "message": "Connection refused", "raw_response": None}
```

## Response dict

Every call returns the same shape whether it succeeded or raised:

| Key | Type | Description |
|---|---|---|
| `status` | `int \| None` | HTTP status code, or `None` on network error |
| `data` | `object` | Parsed JSON body, or `None` if not JSON |
| `message` | `str \| None` | Exception message on error, otherwise `None` |
| `raw_response` | `Response \| None` | The raw response object (`requests.Response` or `httpx.Response`) |

## API

### `ThaReq`

```python
ThaReq(*, backend: Literal["requests", "httpx"] = "requests")
```

`backend="httpx"` requires `pip install tha-req-runner[httpx]`.

### `req.get_session()`

```python
req.get_session(
    *,
    status_forcelist: tuple[int, ...] = (500, 502, 503, 504),  # requests only
    allowed_methods: Collection[str] | None = None,             # requests only
    headers: dict[str, str] | None = None,
    timeout: float = 30,
) -> requests.Session | httpx.Client
```

Returns a session configured with automatic retries. Config is applied only on the **first call per thread** — subsequent calls on the same thread return the cached session regardless of args. Two `ThaReq` instances never share a session.

`allowed_methods=None` uses urllib3's safe-method default, which **excludes POST**. To retry POST (e.g. token endpoints):

```python
session = req.get_session(
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET", "POST"]),
)
```

> **httpx note**: `status_forcelist` and `allowed_methods` are ignored for the httpx backend. httpx retry is connection-level only (no status-based retry).

### `req.reset_session()` / `req.close_session()`

Closes and discards the current thread's session. The next `get_session()` call creates a fresh one. Useful when auth tokens rotate or a session enters a bad state. Both methods are equivalent.

### `ThaReq.parse_response()`

```python
ThaReq.parse_response(result) -> dict[str, Any]
```

Normalizes a response object or a caught exception into a consistent dict. Works with both `requests.Response` and `httpx.Response`. Also callable as an instance method.

### `req.safe_call()`

```python
req.safe_call(fn, *args, **kwargs) -> dict[str, Any]
```

Calls `fn(*args, **kwargs)`, catches any exception, and returns a normalized response dict. Automatically injects the session `timeout` unless the caller provides one.

```python
result = req.safe_call(session.get, url, params={"limit": 100})
result = req.safe_call(session.post, token_url, data={"grant_type": "client_credentials"})
result = req.safe_call(session.get, url, timeout=5)  # override per-call
```

## Session and retries

- **Thread-safe**: each thread gets its own session via `threading.local` on the instance
- **Retry defaults**: `total=3`, `backoff_factor=0.5` (delays: 0.5s → 1s → 2s)
- **Retry statuses**: `500`, `502`, `503`, `504` by default (requests backend only)
- **POST not retried by default** — pass `allowed_methods` explicitly to enable it (requests backend only)
- **Default timeout**: 30s, injected automatically by `safe_call`
- Sessions are reused across calls on the same thread

## Backend comparison

| Feature | `requests` (default) | `httpx` |
|---|---|---|
| Status-based retry | Yes (`status_forcelist`) | No |
| Allowed methods config | Yes | No |
| Default timeout | Yes | Yes |
| Default headers | Yes | Yes |
| Thread-safe sessions | Yes | Yes |
| HTTP/2 | No | Yes |
| Async support | No | Yes (use `httpx.AsyncClient` directly) |

## Used by

- `tha-edfi-runner` — uses `ThaReq` as its HTTP transport layer

## License

MIT
