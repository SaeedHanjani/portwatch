"""Asynchronous TCP connect scanner."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Iterable

from portwatch.config import Config
from portwatch.report import HostResult, evaluate


async def _probe(host: str, port: int, timeout: float) -> bool:
    """Return True if a TCP connection to host:port succeeds within ``timeout``."""
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except (OSError, asyncio.TimeoutError):
        return False
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return True


async def scan_many(
    jobs: Iterable[tuple[str, int]],
    timeout: float,
    concurrency: int,
) -> dict[str, set[int]]:
    """Probe every (host, port) pair using a fixed pool of workers.

    A worker pool pulling from a shared iterator keeps memory flat even for
    hundreds of thousands of probes (a plain ``gather`` would create one task each).
    """
    open_ports: dict[str, set[int]] = defaultdict(set)
    pending = iter(jobs)

    async def worker() -> None:
        # next() on the shared iterator is synchronous, so workers never race.
        for host, port in pending:
            if await _probe(host, port, timeout):
                open_ports[host].add(port)

    await asyncio.gather(*(worker() for _ in range(concurrency)))
    return dict(open_ports)


async def scan(config: Config) -> list[HostResult]:
    """Scan every target in ``config`` and compare against its expectations."""
    # Hosts shared by several targets are probed once, on the union of their ports.
    wanted: dict[str, set[int]] = {}
    for target in config.targets:
        for host in target.hosts:
            wanted.setdefault(host, set()).update(target.ports)

    jobs = ((host, port) for host, ports in wanted.items() for port in sorted(ports))
    found = await scan_many(jobs, config.timeout, config.concurrency)

    results: list[HostResult] = []
    for target in config.targets:
        for host in target.hosts:
            open_here = found.get(host, set()) & target.ports
            results.append(evaluate(target.name, host, open_here, target.expected_open))
    return results
