# tha-req-runner

[![CI](https://github.com/tha-guy-nate/tha-req-runner/actions/workflows/ci.yml/badge.svg)](https://github.com/tha-guy-nate/tha-req-runner/actions/workflows/ci.yml)

A small Python library that provides a thread-safe `requests.Session` with automatic retries and a normalized response parser. Intended as the HTTP transport layer for other `tha-*` runners.

## Install

```bash
pip install tha-req-runner
```

## Quick start

```python
from tha_req_runner import ThaReq

req = ThaReq()
session = req.get_session()

# safe_call wraps the try/except for you
result = req.safe_call(session.get, "https://api.example.com/students", params={"limit": 100})
# {"status": 200, "data": [...], "message": None, "raw_response": <Response>}

# network errors return the same shape — no try/except needed
result = req.safe_call(session.get, "https://unreachable.example.com")
# {"status": None, "data": None, "message": "Connection refused", "raw_response": None}
```

## Response dict

Every method returns the same shape whether the call succeeded or raised:

| Key | Type | Description |
|---|---|---|
| `status` | `int \| None` | HTTP status code, or `None` on network error |
| `data` | `object` | Parsed JSON body, or `None` if not JSON |
| `message` | `str \| None` | Exception message on error, otherwise `None` |
| `raw_response` | `Response \| None` | The raw `requests.Response` object |

## API

### `ThaReq`

```python
ThaReq()
```

### `req.get_session()`

```python
req.get_session(
    *,
    status_forcelist: tuple[int, ...] = (500, 502, 503, 504),
    allowed_methods: Collection[str] | None = None,
) -> requests.Session
```

Returns a `requests.Session` configured with automatic retries (`total=3`, `backoff_factor=0.5`). Config is applied only on the **first call per thread** — subsequent calls on the same thread return the cached session regardless of args. Two `ThaReq` instances never share a session.

`allowed_methods=None` uses urllib3's safe-method default, which **excludes POST**. To retry POST (e.g. token endpoints):

```python
session = req.get_session(
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET", "POST"]),
)
```

### `ThaReq.parse_response()`

```python
ThaReq.parse_response(result: requests.Response | Exception) -> dict[str, Any]
```

Normalizes a `requests.Response` or a caught `Exception` into a consistent dict. Also callable as `req.parse_response(result)` without instantiation.

### `req.safe_call()`

```python
req.safe_call(fn, *args, **kwargs) -> dict[str, Any]
```

Calls `fn(*args, **kwargs)`, catches any exception, and returns a normalized response dict. Equivalent to:

```python
try:
    result = req.parse_response(fn(*args, **kwargs))
except Exception as exc:
    result = req.parse_response(exc)
```

```python
result = req.safe_call(session.get, url, params={"limit": 100})
result = req.safe_call(session.post, token_url, data={"grant_type": "client_credentials"})
```

## Session and retries

- **Thread-safe**: each thread gets its own session via `threading.local` on the instance
- **Retry defaults**: `total=3`, `backoff_factor=0.5` (delays: 0.5s → 1s → 2s)
- **Retry statuses**: `500`, `502`, `503`, `504` by default
- **POST not retried by default** — pass `allowed_methods` explicitly to enable it
- Sessions are reused across calls on the same thread

## Used by

- `tha-edfi-runner` — uses `ThaReq` as its HTTP transport layer

## License

MIT
