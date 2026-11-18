from prometheus_client import generate_latest

from portwatch.metrics import Metrics
from portwatch.report import evaluate


def test_metrics_reflect_results_and_drop_stale_series():
    metrics = Metrics()
    metrics.update([evaluate("web", "10.0.0.5", [22, 80], [80, 443])], duration=1.5)
    text = generate_latest(metrics.registry).decode()
    assert 'portwatch_port_open{host="10.0.0.5",port="80",target="web"} 1.0' in text
    assert 'portwatch_port_open{host="10.0.0.5",port="443",target="web"} 0.0' in text
    assert 'portwatch_unexpected_open_ports{host="10.0.0.5",target="web"} 1.0' in text

    metrics.update([evaluate("web", "10.0.0.5", [80, 443], [80, 443])], duration=1.0)
    text = generate_latest(metrics.registry).decode()
    assert 'port="22"' not in text
    assert 'portwatch_unexpected_open_ports{host="10.0.0.5",target="web"} 0.0' in text
