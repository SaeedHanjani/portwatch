import json

from portwatch.report import evaluate, format_json, format_markdown, format_text, summarize


def test_evaluate_finds_drift_in_both_directions():
    result = evaluate("web", "10.0.0.5", open_ports=[22, 80], expected_open=[80, 443])
    assert result.open_ports == (22, 80)
    assert result.unexpected_open == (22,)
    assert result.expected_closed == (443,)
    assert not result.ok


def test_evaluate_ok_when_matching():
    assert evaluate("web", "10.0.0.5", [80, 443], [443, 80]).ok


def test_summarize_counts():
    results = [
        evaluate("a", "1.1.1.1", [80], [80]),
        evaluate("b", "1.1.1.2", [22], [80]),
    ]
    assert summarize(results) == {
        "hosts": 2,
        "hosts_with_findings": 1,
        "unexpected_open": 1,
        "expected_closed": 1,
    }


def test_formats_render_findings():
    results = [evaluate("db", "10.0.0.9", [22, 3306], [3306, 5432])]
    text = format_text(results)
    assert "[FAIL] db (10.0.0.9)" in text
    assert "unexpected open: 22" in text
    assert "expected but closed: 5432" in text

    data = json.loads(format_json(results))
    assert data["summary"]["hosts_with_findings"] == 1
    assert data["results"][0]["unexpected_open"] == [22]
    assert data["results"][0]["ok"] is False

    assert "❌" in format_markdown(results)
