"""Domain grouping / categorization tests."""

from app.monitor.base import Connection
from app.services.aggregation import aggregate_domains, categorize, registrable_domain


def test_registrable_basic():
    assert registrable_domain("accounts.google.com") == "google.com"
    assert registrable_domain("marketplace.visualstudio.com") == "visualstudio.com"
    assert registrable_domain("google.com") == "google.com"
    assert registrable_domain("www.example.com") == "example.com"


def test_registrable_multi_part_suffix():
    assert registrable_domain("news.bbc.co.uk") == "bbc.co.uk"
    assert registrable_domain("store.amazon.com.au") == "amazon.com.au"
    assert registrable_domain("sub.example.co.uk") == "example.co.uk"


def test_registrable_edge_cases():
    assert registrable_domain("") == ""
    assert registrable_domain("142.250.196.110") == "142.250.196.110"
    assert registrable_domain("localhost") == "localhost"
    assert registrable_domain("EXAMPLE.COM.") == "example.com"


def test_categorize_ads_before_google():
    assert categorize("pagead2.googlesyndication.com") == "Ads"
    assert categorize("ad.doubleclick.net") == "Ads"
    assert categorize("www.google.com") == "Google"
    assert categorize("youtube.com") == "Google"


def test_categorize_brands():
    assert categorize("api.github.com") == "GitHub"
    assert categorize("akamaized.net") == "CDN"
    assert categorize("cdn.jsdelivr.net") == "Cloudflare"
    assert categorize("static.xx.fbcdn.net") == "Meta"
    assert categorize("registry.npmjs.org") == "Developer"
    assert categorize("mystery.example") == "Other"
    assert categorize("8.8.8.8") == "IP"
    assert categorize("") == "Other"


def _conn(process, hostname, ip, port=443) -> Connection:
    c = Connection(
        conn_id=f"1:tcp:10.0.0.1:1:{ip}:{port}",
        pid=1,
        process=process,
        protocol="tcp",
        family="inet4",
        local_ip="10.0.0.1",
        local_port=1,
        remote_ip=ip,
        remote_port=port,
        status="ESTABLISHED",
        hostname=hostname,
    )
    from app.services.aggregation import categorize as cat
    from app.services.aggregation import registrable_domain as reg

    if hostname:
        c.registrable = reg(hostname)
        c.category = cat(hostname)
    return c


def test_aggregate_domains():
    conns = [
        _conn("Chrome", "www.google.com", "1.1.1.1"),
        _conn("Chrome", "accounts.google.com", "1.1.1.2"),
        _conn("VS Code", "api.github.com", "2.2.2.2"),
        _conn("Chrome", "", "9.9.9.9"),  # unresolved
    ]
    rows = aggregate_domains(conns)
    by_domain = {r["domain"]: r for r in rows}
    # google.com rolls up two connections
    assert by_domain["google.com"]["connections"] == 2
    assert by_domain["google.com"]["processes"] == ["Chrome"]
    assert set(by_domain["google.com"]["hosts"]) == {"www.google.com", "accounts.google.com"}
    assert by_domain["github.com"]["connections"] == 1
    # unresolved IP grouped under the IP itself
    assert by_domain["9.9.9.9"]["connections"] == 1
    # sorted by connection count desc
    assert rows[0]["domain"] == "google.com"
