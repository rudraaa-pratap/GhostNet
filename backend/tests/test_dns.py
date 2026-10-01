"""DNS resolver cache tests."""

import time

from app.services.dns import _FAIL_TTL, _SUCCESS_TTL, DnsResolver


def test_invalid_ip_returns_empty_fast():
    r = DnsResolver()
    assert r.resolve_sync("999.999.999.999") == ""


def test_localhost_resolves():
    r = DnsResolver()
    name = r.resolve_sync("127.0.0.1")
    assert name in ("localhost", "")  # some environments lack PTR


def test_failure_is_cached():
    r = DnsResolver()
    assert r.resolve_sync("203.0.113.77") == ""  # TEST-NET-3, no PTR
    # second call served from cache without a new lookup
    entry = r._cache["203.0.113.77"]
    assert entry[0] == ""
    assert entry[1] > time.monotonic() + (_FAIL_TTL - 5)


def test_cache_expiry():
    r = DnsResolver()
    r._cache["1.2.3.4"] = ("old.example.com", time.monotonic() - 1)
    assert r.get_cached("1.2.3.4") is None
    assert "1.2.3.4" not in r._cache


def test_wildcard_ips_skipped():
    import asyncio

    r = DnsResolver()
    assert asyncio.run(r.resolve("0.0.0.0")) == ""
    assert asyncio.run(r.resolve("")) == ""
    assert asyncio.run(r.resolve("::")) == ""


def test_success_ttl_constant():
    assert _SUCCESS_TTL >= 60
    assert _FAIL_TTL < _SUCCESS_TTL
