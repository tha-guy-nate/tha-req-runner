import threading
from unittest.mock import MagicMock

import pytest
import requests

from tha_req_runner import ThaReq


# --- helpers ---

def _mock_resp(status_code: int = 200, json_data: object = None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("no json")
    return resp


# --- get_session ---

def test_get_session_returns_session(req: ThaReq) -> None:
    assert isinstance(req.get_session(), requests.Session)


def test_get_session_same_instance_per_thread(req: ThaReq) -> None:
    assert req.get_session() is req.get_session()


def test_get_session_thread_local(req: ThaReq) -> None:
    sessions: list[requests.Session] = []

    def capture() -> None:
        sessions.append(req.get_session())

    t1 = threading.Thread(target=capture)
    t2 = threading.Thread(target=capture)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(sessions) == 2
    assert sessions[0] is not sessions[1]


def test_get_session_instances_independent() -> None:
    assert ThaReq().get_session() is not ThaReq().get_session()


def test_get_session_default_status_forcelist(req: ThaReq) -> None:
    adapter = req.get_session().get_adapter("https://example.com")
    for code in (500, 502, 503, 504):
        assert code in adapter.max_retries.status_forcelist


def test_get_session_custom_status_forcelist() -> None:
    req = ThaReq()
    adapter = req.get_session(status_forcelist=(429, 503)).get_adapter("https://example.com")
    assert 429 in adapter.max_retries.status_forcelist
    assert 503 in adapter.max_retries.status_forcelist
    assert 500 not in adapter.max_retries.status_forcelist


def test_get_session_allowed_methods_frozenset() -> None:
    req = ThaReq()
    adapter = req.get_session(allowed_methods=frozenset(["GET", "POST"])).get_adapter("https://example.com")
    assert "POST" in adapter.max_retries.allowed_methods


def test_get_session_allowed_methods_list() -> None:
    req = ThaReq()
    adapter = req.get_session(allowed_methods=["GET", "POST"]).get_adapter("https://example.com")
    assert "POST" in adapter.max_retries.allowed_methods


def test_get_session_mounts_http_and_https(req: ThaReq) -> None:
    session = req.get_session()
    assert session.get_adapter("https://example.com") is not None
    assert session.get_adapter("http://example.com") is not None


# --- parse_response ---

def test_parse_success_json() -> None:
    resp = _mock_resp(200, {"id": 1})
    result = ThaReq.parse_response(resp)
    assert result["status"] == 200
    assert result["data"] == {"id": 1}
    assert result["message"] is None
    assert result["raw_response"] is resp


def test_parse_success_non_json() -> None:
    resp = _mock_resp(200)
    result = ThaReq.parse_response(resp)
    assert result["status"] == 200
    assert result["data"] is None
    assert result["message"] is None


def test_parse_exception_no_response() -> None:
    exc = ConnectionError("timed out")
    result = ThaReq.parse_response(exc)
    assert result["status"] is None
    assert result["data"] is None
    assert "timed out" in result["message"]
    assert result["raw_response"] is None


def test_parse_exception_with_response() -> None:
    raw = _mock_resp(401)
    exc = requests.HTTPError("401 Unauthorized", response=raw)
    result = ThaReq.parse_response(exc)
    assert result["status"] == 401
    assert result["raw_response"] is raw
    assert result["data"] is None


def test_parse_callable_as_static(req: ThaReq) -> None:
    result = req.parse_response(_mock_resp(204))
    assert result["status"] == 204


# --- safe_call ---

def test_safe_call_success(req: ThaReq) -> None:
    resp = _mock_resp(200, {"id": 1})
    result = req.safe_call(lambda: resp)
    assert result["status"] == 200
    assert result["data"] == {"id": 1}


def test_safe_call_exception(req: ThaReq) -> None:
    def boom() -> requests.Response:
        raise ConnectionError("refused")

    result = req.safe_call(boom)
    assert result["status"] is None
    assert "refused" in result["message"]


def test_safe_call_passes_args_and_kwargs(req: ThaReq) -> None:
    calls: list[tuple[object, ...]] = []

    def fn(url: str, **kwargs: object) -> requests.Response:
        calls.append((url, kwargs))
        return _mock_resp(200, {})

    req.safe_call(fn, "https://example.com", headers={"X-Key": "v"})
    assert calls[0] == ("https://example.com", {"headers": {"X-Key": "v"}})


def test_safe_call_stores_nothing_on_instance(req: ThaReq) -> None:
    req.safe_call(lambda: _mock_resp(200, {}))
    assert not hasattr(req, "result")
