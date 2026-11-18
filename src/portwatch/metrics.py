"""Prometheus metrics for ``portwatch serve``."""

from __future__ import annotations

import time
from collections.abc import Sequence

from prometheus_client import CollectorRegistry, Gauge, start_http_server

from portwatch.report import HostResult


class Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.port_open = Gauge(
            "portwatch_port_open",
            "1 if the port is open, 0 if it is expected to be open but is closed",
            ["target", "host", "port"],
            registry=self.registry,
        )
        self.unexpected = Gauge(
            "portwatch_unexpected_open_ports",
            "Number of open ports that are not in expected_open",
            ["target", "host"],
            registry=self.registry,
        )
        self.missing = Gauge(
            "portwatch_expected_closed_ports",
            "Number of ports listed in expected_open that are closed",
            ["target", "host"],
            registry=self.registry,
        )
        self.last_scan = Gauge(
            "portwatch_last_scan_timestamp_seconds",
            "Unix time of the last completed scan",
            registry=self.registry,
        )
        self.duration = Gauge(
            "portwatch_scan_duration_seconds",
            "Duration of the last scan",
            registry=self.registry,
        )

    def update(self, results: Sequence[HostResult], duration: float) -> None:
        self.port_open.clear()
        self.unexpected.clear()
        self.missing.clear()
        for r in results:
            for port in r.open_ports:
                self.port_open.labels(r.target, r.host, str(port)).set(1)
            for port in r.expected_closed:
                self.port_open.labels(r.target, r.host, str(port)).set(0)
            self.unexpected.labels(r.target, r.host).set(len(r.unexpected_open))
            self.missing.labels(r.target, r.host).set(len(r.expected_closed))
        self.duration.set(duration)
        self.last_scan.set(time.time())

    def serve(self, address: str, port: int) -> None:
        start_http_server(port, addr=address, registry=self.registry)
