"""nettop parsing + rate derivation tests."""

from app.monitor.bandwidth import BandwidthSampler, _split_endpoint, demo_rates, parse_nettop
from app.monitor.base import Connection

NETTOP_SAMPLE = """\
time,,interface,state,bytes_in,bytes_out,rx_dupe,rx_ooo,re-tx,rtt_avg,rcvsize,tx_win,tc_class,tc_mgt,cc_algo,P,C,R,W,arch,
02:33:11.194107,apsd.365,,,5408,11554,0,0,0,,,,,,,,,,,,
02:34:20.185318,tcp4 172.16.30.1:50421<->17.57.147.5:5223,utun4,Established,5408,11594,0,0,0,
02:34:20.185445,tcp6 *.55294<->*.*,,Listen,,,,,,,,,,-,cubic,-,-,-,-,so,
02:34:06.934083,udp4 *:59426<->*:*,lo0,,0,306,,,,,786896,,BE,,,,,,,so,
02:34:20.185560,tcp4 192.168.1.24:49152<->140.82.113.4:443,,Established,9999,8888,,,,,,,,,
"""


def test_parse_process_rows():
    pids, _ = parse_nettop(NETTOP_SAMPLE)
    assert pids[365] == (5408, 11554)


def test_parse_connection_rows_with_remote():
    _, conns = parse_nettop(NETTOP_SAMPLE)
    assert conns[("tcp", "17.57.147.5", 5223, 50421)] == (5408, 11594)
    assert conns[("tcp", "140.82.113.4", 443, 49152)] == (9999, 8888)


def test_parse_skips_listen_and_wildcard_udp():
    _, conns = parse_nettop(NETTOP_SAMPLE)
    assert all(k[1] != "*" for k in conns)
    assert len(conns) == 2  # established rows only


def test_parse_header_and_empty():
    pids, conns = parse_nettop("")
    assert pids == {} and conns == {}
    pids, conns = parse_nettop("time,,interface,state,bytes_in,bytes_out,\n")
    assert pids == {} and conns == {}


def test_split_endpoint_variants():
    assert _split_endpoint("1.2.3.4:443") == ("1.2.3.4", 443)
    assert _split_endpoint("*:5000") == ("*", 5000)
    assert _split_endpoint("*.55294") == ("*", 55294)
    assert _split_endpoint("[::1]:443") == ("::1", 443)
    assert _split_endpoint("fe80::1%en0:80") == ("fe80::1", 80)


def test_sampler_diff_rates():
    sampler = BandwidthSampler(enabled=False)
    prev = {}
    now = 1000.0
    first = sampler._diff({1: (1000, 500)}, prev, now, key_type=int)
    assert first == {}  # no previous sample → no rate
    second = sampler._diff({1: (3000, 1500)}, prev, now + 2.0, key_type=int)
    assert second[1] == {"rx": 1000.0, "tx": 500.0}


def test_sampler_counter_reset():
    sampler = BandwidthSampler(enabled=False)
    prev = {}
    sampler._diff({1: (5000, 5000)}, prev, 1000.0, key_type=int)
    # process restarted: counter dropped → no bogus negative rate
    rates = sampler._diff({1: (100, 100)}, prev, 1002.0, key_type=int)
    assert rates == {}


def test_sampler_ignores_low_noise():
    sampler = BandwidthSampler(enabled=False)
    prev = {}
    sampler._diff({1: (0, 0)}, prev, 1000.0, key_type=int)  # zero rows not tracked
    assert 1 not in prev


def _conn(pid=42, port=5001) -> Connection:
    return Connection(
        conn_id=f"{pid}:tcp:10.0.0.1:{port}:1.2.3.4:443",
        pid=pid,
        process="Chrome",
        protocol="tcp",
        family="inet4",
        local_ip="10.0.0.1",
        local_port=port,
        remote_ip="1.2.3.4",
        remote_port=443,
        status="ESTABLISHED",
        hostname="google.com",
    )


def test_demo_rates_present_and_positive():
    pid_rates, conn_rates = demo_rates([_conn()], now=100.0)
    assert 42 in pid_rates
    assert pid_rates[42]["rx"] > 0
    conn = _conn()
    assert conn.conn_id in conn_rates
    assert conn_rates[conn.conn_id]["tx"] > 0


def test_demo_rates_scale_with_connections():
    conns = [_conn(pid=1, port=5001), _conn(pid=1, port=5002)]
    pid_rates, _ = demo_rates(conns, now=50.0)
    single, _ = demo_rates([conns[0]], now=50.0)
    # two connections on same pid should not be slower than one
    assert pid_rates[1]["rx"] >= single[1]["rx"] * 0.9
