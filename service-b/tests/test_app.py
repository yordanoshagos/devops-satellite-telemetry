from unittest.mock import patch, Mock

import app as app_module


def valid_frame():
    return {
        "battery_voltage": 14.2,
        "solar_panel_temp": 45.3,
        "gyro_x": 0.01,
        "gyro_y": -0.02,
        "gyro_z": 0.00,
        "signal_strength_dbm": -85,
        "downlink_frequency": 437.5,
    }


def test_validate_checksum_valid_frame():
    assert app_module.validate_checksum(valid_frame()) is True


def test_validate_checksum_missing_field():
    frame = valid_frame()
    del frame["gyro_z"]
    assert app_module.validate_checksum(frame) is False


def test_parse_telemetry_frame_transforms_values():
    parsed = app_module.parse_telemetry_frame(valid_frame())
    assert parsed["battery_voltage_v"] == 14.2
    assert parsed["solar_panel_temp_c"] == 45.3
    assert parsed["gyroscope"] == {"x": 0.01, "y": -0.02, "z": 0.00}
    assert parsed["signal_strength"] == -85
    assert parsed["downlink_freq_mhz"] == 437.5


def test_parse_telemetry_frame_defaults_missing_fields():
    parsed = app_module.parse_telemetry_frame({})
    assert parsed["battery_voltage_v"] == 0.0
    assert parsed["signal_strength"] == -999


def test_health_endpoint():
    client = app_module.app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["service"] == "telemetry-parser"


@patch("app.requests.post")
def test_parse_endpoint_forwards_to_detector(mock_post):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"anomaly_status": "nominal"})
    client = app_module.app.test_client()
    resp = client.post("/parse", json={
        "processing_request_id": "req-test-1",
        "satellite_id": "SAT-001",
        "mission_id": "MISSION-TEST",
        "telemetry_frame": valid_frame(),
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "parsed"
    assert body["checksum_valid"] is True
    mock_post.assert_called_once()


def test_parse_endpoint_rejects_invalid_frame():
    client = app_module.app.test_client()
    frame = valid_frame()
    del frame["battery_voltage"]
    resp = client.post("/parse", json={
        "processing_request_id": "req-test-2",
        "satellite_id": "SAT-001",
        "telemetry_frame": frame,
    })
    assert resp.status_code == 400


@patch("app.requests.post", side_effect=app_module.requests.exceptions.RequestException("boom"))
def test_parse_endpoint_returns_502_when_detector_unreachable(mock_post):
    client = app_module.app.test_client()
    resp = client.post("/parse", json={
        "processing_request_id": "req-test-3",
        "satellite_id": "SAT-001",
        "telemetry_frame": valid_frame(),
    })
    assert resp.status_code == 502


def test_metrics_endpoint_exposes_prometheus_metrics():
    client = app_module.app.test_client()
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body


@patch("app.requests.get")
def test_lab_slow_calls_downstream_and_returns_200(mock_get):
    mock_get.return_value = Mock(status_code=200, json=lambda: {"service": "anomaly-detector"})
    client = app_module.app.test_client()
    resp = client.get("/slow")
    assert resp.status_code == 200
    assert resp.get_json()["lab_only"] is True
    mock_get.assert_called_once()


@patch("app.requests.get")
def test_lab_fail_propagates_500(mock_get):
    mock_get.return_value = Mock(status_code=500, json=lambda: {"error": "injected_failure"})
    client = app_module.app.test_client()
    resp = client.get("/fail")
    assert resp.status_code == 500
    assert resp.get_json()["error"] == "injected_failure"
