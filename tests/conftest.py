import pytest

from tha_req_runner import ThaReq


@pytest.fixture
def req() -> ThaReq:
    return ThaReq()
