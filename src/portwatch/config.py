"""Configuration loading and validation."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PORTS = "1-1024"
MAX_HOSTS_PER_TARGET = 1024


class ConfigError(ValueError):
    """Raised when the configuration file is invalid."""


@dataclass(frozen=True)
class Target:
    """One host or network to scan, plus the ports that are *supposed* to be open."""

    name: str
    hosts: tuple[str, ...]
    expected_open: frozenset[int]
    ports: frozenset[int]


@dataclass(frozen=True)
class Config:
    targets: tuple[Target, ...]
    timeout: float = 1.0
    concurrency: int = 200


def parse_ports(spec: Any) -> frozenset[int]:
    """Parse ``"22,80,8000-8100"`` (or a list of ints/strings) into a set of ports."""
    if isinstance(spec, bool):
        raise ConfigError(f"invalid port specification: {spec!r}")
    if isinstance(spec, int):
        parts = [str(spec)]
    elif isinstance(spec, str):
        parts = spec.split(",")
    elif isinstance(spec, list):
        parts = [str(item) for item in spec]
    else:
        raise ConfigError(f"ports must be a string, an integer or a list, got {spec!r}")

    ports: set[int] = set()
    for raw in parts:
        part = raw.strip()
        if not part:
            continue
        low_text, sep, high_text = part.partition("-")
        try:
            low = int(low_text)
            high = int(high_text) if sep else low
        except ValueError:
            raise ConfigError(f"invalid port specification: {part!r}") from None
        if not 1 <= low <= high <= 65535:
            raise ConfigError(f"port or range out of bounds (1-65535): {part!r}")
        ports.update(range(low, high + 1))
    return frozenset(ports)


def expand_hosts(host: str) -> tuple[str, ...]:
    """Expand a CIDR network into its host addresses; hostnames and IPs pass through."""
    if "/" not in host:
        return (host,)
    try:
        network = ipaddress.ip_network(host, strict=False)
    except ValueError as exc:
        raise ConfigError(f"invalid network {host!r}: {exc}") from None
    if network.num_addresses > MAX_HOSTS_PER_TARGET + 2:
        raise ConfigError(
            f"network {host!r} is too large (max {MAX_HOSTS_PER_TARGET} hosts per target)"
        )
    return tuple(str(ip) for ip in network.hosts())


def _parse_target(index: int, item: Any) -> Target:
    where = f"targets[{index}]"
    if not isinstance(item, dict):
        raise ConfigError(f"{where} must be a mapping")
    host = item.get("host")
    if not isinstance(host, str) or not host.strip():
        raise ConfigError(f"{where}: 'host' is required")
    host = host.strip()
    try:
        expected = parse_ports(item.get("expected_open") or [])
        ports = parse_ports(item.get("ports", DEFAULT_PORTS)) | expected
        hosts = expand_hosts(host)
    except ConfigError as exc:
        raise ConfigError(f"{where}: {exc}") from None
    return Target(
        name=str(item.get("name", host)),
        hosts=hosts,
        expected_open=expected,
        ports=ports,
    )


def parse_config(raw: Any) -> Config:
    if not isinstance(raw, dict):
        raise ConfigError("the top level of the config must be a mapping")

    timeout = raw.get("timeout", 1.0)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ConfigError("'timeout' must be a positive number (seconds)")

    concurrency = raw.get("concurrency", 200)
    if isinstance(concurrency, bool) or not isinstance(concurrency, int) or concurrency < 1:
        raise ConfigError("'concurrency' must be a positive integer")

    raw_targets = raw.get("targets")
    if not isinstance(raw_targets, list) or not raw_targets:
        raise ConfigError("'targets' must be a non-empty list")

    targets = tuple(_parse_target(i, item) for i, item in enumerate(raw_targets, start=1))
    return Config(targets=targets, timeout=float(timeout), concurrency=concurrency)


def load_config(path: Path | str) -> Config:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc.strerror or exc}") from None
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from None
    return parse_config(raw)
