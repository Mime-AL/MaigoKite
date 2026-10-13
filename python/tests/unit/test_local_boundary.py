"""Loopback policy covers both socket families without accepting remote aliases."""

import pytest
from agent.api.app import loopback


@pytest.mark.parametrize(
    ("host", "allowed"),
    [
        ("localhost", True),
        ("127.0.0.1", True),
        ("127.0.0.2", True),
        ("::1", True),
        ("::ffff:127.0.0.1", True),
        ("::ffff:7f00:1", True),
        ("0.0.0.0", False),
        ("::", False),
        ("192.168.1.1", False),
        ("::ffff:192.168.1.1", False),
        ("2001:db8::1", False),
        ("localhost.example.com", False),
        ("[::1]", False),
        ("", False),
    ],
)
def test_loopback_boundary(host: str, allowed: bool) -> None:
    assert loopback(host) is allowed
