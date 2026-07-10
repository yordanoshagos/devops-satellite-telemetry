from unittest.mock import patch, Mock

import app as app_module


def nominal_parsed_data():
    return {
        "battery_voltage_v": 14.2,
        "solar_panel_temp_c": 45.3,
        "signal_strength": -85,
        "gyroscope": {"x": 0.01, "y": -0.02, "z": 0.00},
    }


def test_check_anomalies_nominal():
    status, anomalies = app_module.check_anomalies(nominal_parsed_data())
    assert status == "nominal"
    assert anomalies == []


def test_check_anomalies_warning_low_battery():
    data = nominal_parsed_data()
    data["battery_voltage_v"] = 11.5  # below min (12.0) but above critical_low (11.0)
    status, anomalies = app_module.check_anomalies(data)
    assert status == "warning"
    assert any(a["sensor"] == "battery_voltage_v" and a["severity"] == "warning" for a in anomalies)


def test_check_anomalies_critical_low_battery():
    data = nominal_parsed_data()
    data["battery_voltage_v"] = 10.5  # below critical_low (11.0)
    status, anomalies = app_module.check_anomalies(data)
    assert status == "critical"
    assert any(a["sensor"] == "battery_voltage_v" and a["severity"] == "critical" for a in anomalies)


def test_check_anomalies_critical_overrides_warning():
    data = nominal_parsed_data()
    data["battery_voltage_v"] = 10.5  # critical
    data["solar_panel_temp_c"] = 85.0  # warning (above max 80, below critical_high 90)
    status, anomalies = app_module.check_anomalies(data)
    assert status == "critical"
    assert len(anomalies) == 2


def test_check_anomalies_gyro_deviation():
    data = nominal_parsed_data()
    data["gyroscope"] = {"x": 5.5, "y": 0.0, "z": 0.0}
    status, anomalies = app_module.check_anomalies(data)
    assert status == "warning"
    assert any(a["sensor"] == "gyroscope_x" for a in anomalies)


def test_health_endpoint():
    client = app_module.app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["service"] == "anomaly-detector"
    assert body["status"] == "operational"


@patch("app.requests.post")
def test_analyze_endpoint_nominal(mock_post):
    mock_post.return_value = Mock(status_code=200)
    client = app_module.app.test_client()
    resp = client.post("/analyze", json={
        "processing_request_id": "req-test-1",
        "satellite_id": "SAT-001",
        "mission_id": "MISSION-TEST",
        "parsed_data": nominal_parsed_data(),
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "analyzed"
    assert body["anomaly_status"] == "nominal"
    mock_post.assert_called_once()


@patch("app.requests.post")
def test_analyze_endpoint_critical(mock_post):
    mock_post.return_value = Mock(status_code=200)
    client = app_module.app.test_client()
    data = nominal_parsed_data()
    data["battery_voltage_v"] = 10.5
    resp = client.post("/analyze", json={
        "processing_request_id": "req-test-2",
        "satellite_id": "SAT-001",
        "mission_id": "MISSION-TEST",
        "parsed_data": data,
    })
    assert resp.status_code == 200
    assert resp.get_json()["anomaly_status"] == "critical"


def test_analyze_endpoint_rejects_empty_payload():
    client = app_module.app.test_client()
    resp = client.post("/analyze", json={})
    assert resp.status_code == 400


def test_metrics_endpoint_exposes_prometheus_metrics():
    client = app_module.app.test_client()
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "http_requests_total" in body
    assert "service_up" in body


def test_lab_fail_returns_500():
    client = app_module.app.test_client()
    resp = client.get("/fail")
    assert resp.status_code == 500
    assert resp.get_json()["lab_only"] is True


def test_lab_slow_returns_200():
    # LAB_SLOW_SECONDS is 0 under test (see conftest), so this is fast.
    client = app_module.app.test_client()
    resp = client.get("/slow")
    assert resp.status_code == 200
    assert resp.get_json()["lab_only"] is True