import pytest


@pytest.fixture(autouse=True)
def block_network_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every test fail instead of accidentally reaching the network."""
    monkeypatch.delattr("requests.sessions.Session.request")
