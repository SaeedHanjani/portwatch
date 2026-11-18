"""Compare scan results with expectations and render reports."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HostResult:
    target: str
    host: str
    open_ports: tuple[int, ...]
    unexpected_open: tuple[int, ...]
    expected_closed: tuple[int, ...]

    @property
    def ok(self) -> bool:
        return not (self.unexpected_open or self.expected_closed)


def evaluate(
    target: str,
    host: str,
    open_ports: Iterable[int],
    expected_open: Iterable[int],
) -> HostResult:
    """Build a result by comparing what is open with what *should* be open."""
    opened = frozenset(open_ports)
    expected = frozenset(expected_open)
    return HostResult(
        target=target,
        host=host,
        open_ports=tuple(sorted(opened)),
        unexpected_open=tuple(sorted(opened - expected)),
        expected_closed=tuple(sorted(expected - opened)),
    )


def summarize(results: Sequence[HostResult]) -> dict[str, int]:
    return {
        "hosts": len(results),
        "hosts_with_findings": sum(not r.ok for r in results),
        "unexpected_open": sum(len(r.unexpected_open) for r in results),
        "expected_closed": sum(len(r.expected_closed) for r in results),
    }


def _ports(ports: Iterable[int]) -> str:
    return ", ".join(str(p) for p in ports) or "-"


def format_text(results: Sequence[HostResult]) -> str:
    lines: list[str] = []
    for r in results:
        marker = "[ OK ]" if r.ok else "[FAIL]"
        lines.append(f"{marker} {r.target} ({r.host})  open: {_ports(r.open_ports)}")
        if r.unexpected_open:
            lines.append(f"         unexpected open: {_ports(r.unexpected_open)}")
        if r.expected_closed:
            lines.append(f"         expected but closed: {_ports(r.expected_closed)}")
    s = summarize(results)
    lines.append("")
    lines.append(
        f"{s['hosts']} host(s) scanned, {s['hosts_with_findings']} with findings "
        f"({s['unexpected_open']} unexpected open, {s['expected_closed']} expected but closed)"
    )
    return "\n".join(lines)


def format_json(results: Sequence[HostResult]) -> str:
    payload = {
        "summary": summarize(results),
        "results": [{**asdict(r), "ok": r.ok} for r in results],
    }
    return json.dumps(payload, indent=2)


def format_markdown(results: Sequence[HostResult]) -> str:
    lines = [
        "| Status | Target | Host | Open | Unexpected open | Expected but closed |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        status = "✅" if r.ok else "❌"
        lines.append(
            f"| {status} | {r.target} | {r.host} | {_ports(r.open_ports)} "
            f"| {_ports(r.unexpected_open)} | {_ports(r.expected_closed)} |"
        )
    return "\n".join(lines)


FORMATTERS: dict[str, Callable[[Sequence[HostResult]], str]] = {
    "text": format_text,
    "json": format_json,
    "markdown": format_markdown,
}
