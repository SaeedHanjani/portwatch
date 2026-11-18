import socket
from collections.abc import Iterator

import pytest


@pytest.fixture
def listening_port() -> Iterator[int]:
    """A local TCP port that accepts connections (the kernel backlog is enough)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        yield sock.getsockname()[1]


@pytest.fixture
def closed_port() -> int:
    """A local TCP port that nothing is listening on."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
