"""lsof -F output parser tests."""

from app.monitor.macos import parse_lsof_fields

SAMPLE = """\
p1339
cGoogle Chrome Helper
f28
PTCP
n172.16.30.1:50693->142.251.16.188:5228
TST=ESTABLISHED
TQR=12
TQS=34
f29
PTCP
n172.16.30.1:50694->142.251.16.188:443
TST=ESTABLISHED
p701
cmongod
f9
PTCP
n127.0.0.1:27017
TST=LISTEN
f10
PTCP
n[::1]:27017
TST=LISTEN
p750
cSpotify
f43
PUDP
n*:57621
"""

LISTEN = """\
p900
cServer
f4
PTCP
n*:8080
TST=LISTEN
f5
PTCP
n*:8080
TST=LISTEN
"""


def test_parse_basic_fields():
    raws = parse_lsof_fields(SAMPLE)
    assert len(raws) == 5
    chrome = [r for r in raws if r.process == "Google Chrome Helper"]
    assert len(chrome) == 2
    c = chrome[0]
    assert c.pid == 1339
    assert c.protocol == "tcp"
    assert c.local_ip == "172.16.30.1"
    assert c.local_port == 50693
    assert c.remote_ip == "142.251.16.188"
    assert c.remote_port == 5228
    assert c.status == "ESTABLISHED"


def test_parse_listen_and_ipv6():
    raws = parse_lsof_fields(SAMPLE)
    mongo = [r for r in raws if r.process == "mongod"]
    assert {r.status for r in mongo} == {"LISTEN"}
    assert {r.family for r in mongo} == {"inet4", "inet6"}
    assert all(r.remote_ip == "" for r in mongo)


def test_parse_udp():
    raws = parse_lsof_fields(SAMPLE)
    udp = [r for r in raws if r.protocol == "udp"]
    assert len(udp) == 1
    assert udp[0].status == "UDP"
    assert udp[0].remote_ip == ""


def test_duplicate_fds_deduped():
    raws = parse_lsof_fields(LISTEN)
    assert len(raws) == 1
    assert raws[0].key == "900:tcp:*:8080::0"


def test_empty_and_garbage():
    assert parse_lsof_fields("") == []
    assert parse_lsof_fields("pnotanumber\ncX\n") == []
