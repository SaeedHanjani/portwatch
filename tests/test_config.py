import pytest

from portwatch.config import (
    ConfigError,
    expand_hosts,
    load_config,
    parse_config,
    parse_ports,
)


def test_parse_ports_mixed_spec():
    assert parse_ports("22, 80,8000-8002") == {22, 80, 8000, 8001, 8002}


def test_parse_ports_accepts_list_and_int():
    assert parse_ports([80, "443"]) == {80, 443}
    assert parse_ports(8080) == {8080}


@pytest.mark.parametrize("spec", ["abc", "0", "70000", "90-80", "-5", True, 1.5])
def test_parse_ports_rejects_bad_input(spec):
    with pytest.raises(ConfigError):
        parse_ports(spec)


def test_expand_hosts_cidr_skips_network_and_broadcast():
    assert expand_hosts("192.168.1.0/30") == ("192.168.1.1", "192.168.1.2")


def test_expand_hosts_passes_hostnames_through():
    assert expand_hosts("example.internal") == ("example.internal",)


def test_expand_hosts_rejects_huge_network():
    with pytest.raises(ConfigError, match="too large"):
        expand_hosts("10.0.0.0/8")


def test_parse_config_defaults_and_expected_ports_are_scanned():
    config = parse_config({"targets": [{"host": "10.0.0.5", "expected_open": [80], "ports": "22"}]})
    target = config.targets[0]
    assert target.name == "10.0.0.5"
    assert target.ports == {22, 80}  # expected ports are always scanned
    assert config.timeout == 1.0 and config.concurrency == 200


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"targets": []},
        {"targets": [{"name": "no-host"}]},
        {"targets": [{"host": "x"}], "timeout": 0},
        {"targets": [{"host": "x"}], "concurrency": 0},
    ],
)
def test_parse_config_rejects_invalid(raw):
    with pytest.raises(ConfigError):
        parse_config(raw)


def test_load_config_reports_missing_and_broken_files(tmp_path):
    with pytest.raises(ConfigError, match="cannot read"):
        load_config(tmp_path / "nope.yaml")
    broken = tmp_path / "broken.yaml"
    broken.write_text("targets: [unclosed")
    with pytest.raises(ConfigError, match="invalid YAML"):
        load_config(broken)
