"""Command line interface."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path

from portwatch import __version__
from portwatch.config import ConfigError, load_config
from portwatch.metrics import Metrics
from portwatch.report import FORMATTERS, summarize
from portwatch.scanner import scan

log = logging.getLogger("portwatch")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portwatch",
        description="Detect unexpected open ports and missing services on networks you own.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_cmd = sub.add_parser("scan", help="run one scan and print a report")
    scan_cmd.add_argument("-c", "--config", type=Path, required=True, help="path to YAML config")
    scan_cmd.add_argument(
        "-f", "--format", choices=sorted(FORMATTERS), default="text", help="report format"
    )

    serve_cmd = sub.add_parser("serve", help="scan periodically and expose Prometheus metrics")
    serve_cmd.add_argument("-c", "--config", type=Path, required=True, help="path to YAML config")
    serve_cmd.add_argument("--interval", type=float, default=300, help="seconds between scans")
    serve_cmd.add_argument("--listen-address", default="0.0.0.0", help="metrics bind address")
    serve_cmd.add_argument("--listen-port", type=int, default=9877, help="metrics port")
    return parser


def _cmd_scan(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    results = asyncio.run(scan(config))
    print(FORMATTERS[args.format](results))
    return 0 if all(r.ok for r in results) else 1


def _cmd_serve(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    metrics = Metrics()
    metrics.serve(args.listen_address, args.listen_port)
    log.info("metrics on http://%s:%d/metrics", args.listen_address, args.listen_port)

    # Docker sends SIGTERM and Python as PID 1 ignores it by default: handle it explicitly.
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    while not stop.is_set():
        started = time.monotonic()
        results = asyncio.run(scan(config))
        elapsed = time.monotonic() - started
        metrics.update(results, elapsed)
        s = summarize(results)
        log.info(
            "scan finished in %.1fs: %d host(s), %d with findings",
            elapsed,
            s["hosts"],
            s["hosts_with_findings"],
        )
        stop.wait(args.interval)
    log.info("shutting down")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        if args.command == "scan":
            return _cmd_scan(args)
        return _cmd_serve(args)
    except ConfigError as exc:
        print(f"portwatch: config error: {exc}", file=sys.stderr)
        return 2
