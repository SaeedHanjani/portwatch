import json

from portwatch.cli import main


def _write(tmp_path, body):
    path = tmp_path / "targets.yaml"
    path.write_text(body)
    return path


def test_scan_exit_0_when_everything_matches(tmp_path, listening_port, capsys):
    cfg = _write(
        tmp_path,
        f"targets:\n  - host: 127.0.0.1\n    expected_open: [{listening_port}]\n"
        f"    ports: '{listening_port}'\n",
    )
    assert main(["scan", "-c", str(cfg)]) == 0
    assert "[ OK ]" in capsys.readouterr().out


def test_scan_exit_1_on_drift_and_json_output(tmp_path, listening_port, closed_port, capsys):
    cfg = _write(
        tmp_path,
        f"targets:\n  - host: 127.0.0.1\n    expected_open: [{closed_port}]\n"
        f"    ports: '{listening_port}'\n",
    )
    assert main(["scan", "-c", str(cfg), "-f", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["results"][0]["unexpected_open"] == [listening_port]
    assert data["results"][0]["expected_closed"] == [closed_port]


def test_scan_exit_2_on_bad_config(tmp_path, capsys):
    cfg = _write(tmp_path, "targets: []\n")
    assert main(["scan", "-c", str(cfg)]) == 2
    assert "config error" in capsys.readouterr().err
