"""Domain grouping: registrable-domain extraction, categories, roll-ups."""

from __future__ import annotations

import ipaddress

from ..monitor.base import Connection

# Common multi-part public suffixes (keeps this local-first — no PSL fetch).
_MULTI_PART_SUFFIXES = frozenset(
    {
        "co.uk",
        "org.uk",
        "ac.uk",
        "gov.uk",
        "me.uk",
        "net.uk",
        "sch.uk",
        "com.au",
        "net.au",
        "org.au",
        "edu.au",
        "gov.au",
        "id.au",
        "co.jp",
        "ne.jp",
        "or.jp",
        "ac.jp",
        "go.jp",
        "com.br",
        "net.br",
        "org.br",
        "com.mx",
        "com.ar",
        "com.cn",
        "net.cn",
        "org.cn",
        "com.tw",
        "org.tw",
        "com.hk",
        "com.sg",
        "co.nz",
        "org.nz",
        "co.za",
        "co.in",
        "firm.in",
        "gen.in",
        "ind.in",
        "co.kr",
        "or.kr",
        "co.il",
        "com.tr",
        "com.pl",
        "com.ua",
        "co.in",
        "gov.in",
        "nic.in",
        "blogspot.com",
    }
)

# Ordered: more specific rules first (e.g. Ads must match before Google).
_CATEGORY_RULES: list[tuple[tuple[str, ...], str]] = [
    # advertising / tracking
    (
        (
            "doubleclick",
            "googlesyndication",
            "googleadservices",
            "googletagmanager",
            "google-analytics",
            "adnxs",
            "adsrvr",
            "taboola",
            "outbrain",
            "criteo",
            "pubmatic",
            "rubiconproject",
            "openx",
            "smartadserver",
            "moatads",
            "scorecardresearch",
        ),
        "Ads",
    ),
    # telemetry / analytics / crash reporting
    (
        (
            "segment.",
            "mixpanel",
            "amplitude",
            "hotjar",
            "sentry",
            "datadoghq",
            "newrelic",
            "nr-data",
            "bugsnag",
            "fullstory",
            "heap.io",
            "branch.io",
            "appsflyer",
            "adjust.com",
            "telemetry",
        ),
        "Analytics",
    ),
    # CDNs / edge (before brand rules — akamaized belongs to CDN not the brand)
    (
        (
            "akamaized",
            "akamai",
            "cloudfront",
            "fastly",
            "edgecast",
            "limelight",
            "incapdns",
            "stackpath",
            "cdn77",
        ),
        "CDN",
    ),
    (
        (
            "google",
            "youtube",
            "gstatic",
            "googleapis",
            "ggpht",
            "blogspot",
            "googleusercontent",
            "1e100",
        ),
        "Google",
    ),
    (("github", "githubassets", "githubusercontent"), "GitHub"),
    (("microsoft", "msn", "live.com", "office", "azure", "windows", "bing"), "Microsoft"),
    (("apple", "icloud", "itunes", "mzstatic", "cdn-apple"), "Apple"),
    (("amazon", "aws", "amazonaws", "ssl-images-amazon", "media-amazon"), "Amazon"),
    (("cloudflare", "cdnjs", "jsdelivr"), "Cloudflare"),
    (("facebook", "instagram", "whatsapp", "fbcdn"), "Meta"),
    (("twitter", "twimg", "t.co"), "X / Twitter"),
    (("linkedin", "licdn"), "LinkedIn"),
    (("reddit", "redd.it"), "Reddit"),
    (("discord", "discordapp"), "Discord"),
    (("slack", "slack-edge", "slack-imgs"), "Slack"),
    (("zoom", "zoom.us"), "Zoom"),
    (("spotify", "scdn", "pscdn"), "Spotify"),
    (("netflix", "nflx"), "Netflix"),
    (("twitch", "ttvnw"), "Twitch"),
    (("npmjs", "npmjs.org", "pypi", "pythonhosted", "crates", "rust-lang"), "Developer"),
    (("steam", "steampowered"), "Gaming"),
    (
        (
            "bbc",
            "cnn",
            "nytimes",
            "reuters",
            "guardian",
            "theguardian",
            "washingtonpost",
            "hindustantimes",
        ),
        "News",
    ),
    (("duckduckgo", "brave", "mozilla", "firefox"), "Search / Browser"),
    (("dropbox", "dropboxstatic"), "Storage"),
    (("stripe", "paypal", "adyen", "braintree"), "Payments"),
]


def is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def registrable_domain(host: str) -> str:
    """Best-effort eTLD+1 (e.g. accounts.google.com → google.com).

    IP addresses and single-label hosts are returned unchanged.
    """
    if not host:
        return ""
    host = host.strip(".").lower()
    if not host or is_ip(host):
        return host
    labels = host.split(".")
    if len(labels) < 3:
        return host
    if ".".join(labels[-2:]) in _MULTI_PART_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def categorize(host: str) -> str:
    """Map a hostname/domain to a coarse category label."""
    if not host:
        return "Other"
    if is_ip(host):
        return "IP"
    host = host.lower().strip(".")
    labels = host.split(".")
    for needles, category in _CATEGORY_RULES:
        for label in labels:
            for needle in needles:
                if needle in label:
                    return category
    return "Other"


def aggregate_domains(connections: list[Connection]) -> list[dict]:
    """Roll connections up by registrable domain (PDF §3 domain grouping)."""
    groups: dict[str, dict] = {}
    for c in connections:
        if not c.remote_ip:
            continue
        site = c.registrable or registrable_domain(c.domain)
        row = groups.setdefault(
            site,
            {
                "domain": site,
                "category": c.category or categorize(c.hostname or ""),
                "connections": 0,
                "established": 0,
                "processes": set(),
                "ips": set(),
                "ports": set(),
                "protocols": set(),
                "hosts": set(),
                "first_seen": c.opened_at,
                "last_seen": c.last_seen,
            },
        )
        row["connections"] += 1
        if c.status == "ESTABLISHED":
            row["established"] += 1
        row["processes"].add(c.process)
        row["ips"].add(c.remote_ip)
        if c.remote_port:
            row["ports"].add(c.remote_port)
        row["protocols"].add(c.protocol)
        if c.hostname:
            row["hosts"].add(c.hostname)
        row["first_seen"] = min(row["first_seen"], c.opened_at)
        row["last_seen"] = max(row["last_seen"], c.last_seen)

    out = []
    for row in groups.values():
        row["processes"] = sorted(row["processes"])
        row["ips"] = sorted(row["ips"])
        row["ports"] = sorted(row["ports"])
        row["protocols"] = sorted(row["protocols"])
        row["hosts"] = sorted(row["hosts"])
        out.append(row)
    out.sort(key=lambda r: r["connections"], reverse=True)
    return out
