import asyncio

from portwatch.config import Config, Target
from portwatch.scanner import scan, scan_many


def test_scan_many_detects_open_and_closed(listening_port, closed_port):
    jobs = [("127.0.0.1", listening_port), ("127.0.0.1", closed_port)]
    found = asyncio.run(scan_many(jobs, timeout=1.0, concurrency=4))
    assert found == {"127.0.0.1": {listening_port}}


def test_scan_many_handles_more_jobs_than_workers(listening_port):
    jobs = [("127.0.0.1", listening_port)] * 50
    found = asyncio.run(scan_many(jobs, timeout=1.0, concurrency=3))
    assert found == {"127.0.0.1": {listening_port}}


def test_scan_reports_drift(listening_port, closed_port):
    target = Target(
        name="local",
        hosts=("127.0.0.1",),
        expected_open=frozenset({closed_port}),
        ports=frozenset({listening_port, closed_port}),
    )
    (result,) = asyncio.run(scan(Config(targets=(target,), timeout=1.0, concurrency=4)))
    assert result.unexpected_open == (listening_port,)
    assert result.expected_closed == (closed_port,)


def test_scan_merges_targets_sharing_a_host(listening_port, closed_port):
    shared = dict(hosts=("127.0.0.1",), expected_open=frozenset())
    config = Config(
        targets=(
            Target(name="a", ports=frozenset({listening_port}), **shared),
            Target(name="b", ports=frozenset({closed_port}), **shared),
        )
    )
    a, b = asyncio.run(scan(config))
    assert a.open_ports == (listening_port,)
    assert b.open_ports == ()
