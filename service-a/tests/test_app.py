from unittest.mock import patch, Mock

import app as app_module


@patch("app.requests.get")
def test_health_endpoint_reports_dependencies(mock_get):
    mock_get.return_value = Mock(status_code=200)

    client = app_module.app.test_client()
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["service"] == "ground-station-api"
    assert body["status"] == "operational"
    assert body["dependencies"]["telemetry_parser"] == "reachable"
    assert body["dependencies"]["anomaly_detector"] == "reachable"
    assert mock_get.call_count == 2
    called_urls = [call.args[0] for call in mock_get.call_args_list]
    assert f"{app_module.TELEMETRY_PARSER_BASE_URL}/health" in called_urls
    assert f"{app_module.ANOMALY_DETECTOR_BASE_URL}/health" in called_urls


@patch("app.requests.get")
def test_health_operational_when_only_parser_reachable(mock_get):
    """A→C is denied by SG on ECS; operational depends only on service B."""
    def side_effect(url, timeout=2):
        if "anomaly" in url or "service-c" in url or ":3003" in url:
            raise Exception("connection timed out")
        return Mock(status_code=200)

    mock_get.side_effect = side_effect

    client = app_module.app.test_client()
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "operational"
    assert body["dependencies"]["telemetry_parser"] == "reachable"
    assert "unreachable" in body["dependencies"]["anomaly_detector"]


@patch("app.requests.get", side_effect=Exception("connection refused"))
def test_health_endpoint_reports_unreachable_dependencies(mock_get):
    client = app_module.app.test_client()
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.get_json()
    assert "unreachable" in body["dependencies"]["telemetry_parser"]


@patch("app.requests.post")
def test_telemetry_endpoint_accepts_valid_frame(mock_post):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"status": "parsed"})

    client = app_module.app.test_client()
    resp = client.post(
        "/telemetry",
        json={
            "satellite_id": "SAT-001",
            "mission_id": "MISSION-ALPHA-7",
            "timestamp": "2026-06-18T09:30:00Z",
            "telemetry_frame": {"battery_voltage": 14.2},
        },
    )

    assert resp.status_code == 202
    body = resp.get_json()
    assert body["status"] == "accepted"
    assert body["processing_request_id"].startswith("req-")


@patch("app.requests.post", side_effect=app_module.requests.exceptions.RequestException("boom"))
def test_telemetry_endpoint_returns_502_when_parser_unreachable(mock_post):
    client = app_module.app.test_client()
    resp = client.post(
        "/telemetry",
        json={
            "satellite_id": "SAT-001",
            "mission_id": "MISSION-ALPHA-7",
            "telemetry_frame": {},
        },
    )

    assert resp.status_code == 502


def test_telemetry_endpoint_rejects_empty_payload():
    client = app_module.app.test_client()
    resp = client.post("/telemetry", json={})

    assert resp.status_code == 400


def test_callback_endpoint_requires_processing_request_id():
    client = app_module.app.test_client()
    resp = client.post("/callback", json={"satellite_id": "SAT-001"})

    assert resp.status_code == 400


@patch("app.requests.post")
def test_status_endpoint_tracks_request_lifecycle(mock_post):
    mock_post.return_value = Mock(status_code=200, json=lambda: {"status": "parsed"})

    client = app_module.app.test_client()
    telemetry_resp = client.post(
        "/telemetry",
        json={
            "satellite_id": "SAT-001",
            "mission_id": "MISSION-ALPHA-7",
            "telemetry_frame": {"battery_voltage": 14.2},
        },
    )
    request_id = telemetry_resp.get_json()["processing_request_id"]

    status_resp = client.get(f"/status/{request_id}")

    assert status_resp.status_code == 200
    assert status_resp.get_json()["status"] == "awaiting_callback"


@patch("app.requests.post")
def test_status_endpoint_reports_completed_when_callback_runs_during_parser_call(mock_post):
    client = app_module.app.test_client()

    def parser_triggers_sync_callback(url, **kwargs):
        request_id = kwargs["json"]["processing_request_id"]
        callback_resp = client.post(
            "/callback",
            json={
                "processing_request_id": request_id,
                "satellite_id": "SAT-001",
                "anomaly_status": "nominal",
                "anomalies_detected": [],
            },
        )
        assert callback_resp.status_code == 200
        return Mock(status_code=200, json=lambda: {"status": "parsed"})

    mock_post.side_effect = parser_triggers_sync_callback

    telemetry_resp = client.post(
        "/telemetry",
        json={
            "satellite_id": "SAT-001",
            "mission_id": "MISSION-ALPHA-7",
            "telemetry_frame": {"battery_voltage": 14.2},
        },
    )
    request_id = telemetry_resp.get_json()["processing_request_id"]

    status_resp = client.get(f"/status/{request_id}")
    body = status_resp.get_json()

    assert status_resp.status_code == 200
    assert body["status"] == "completed"
    assert body["anomaly_status"] == "nominal"
    assert body["completed_at"] is not None


def test_status_endpoint_returns_404_for_unknown_request():
    client = app_module.app.test_client()
    resp = client.get("/status/does-not-exist")

    assert resp.status_code == 404


def test_metrics_endpoint_exposes_prometheus_metrics():
    client = app_module.app.test_client()
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "http_requests_total" in body
    assert "http_errors_total" in body


@patch("app.requests.get")
def test_lab_slow_returns_200(mock_get):
    mock_get.return_value = Mock(status_code=200, json=lambda: {"service": "telemetry-parser"})
    client = app_module.app.test_client()
    resp = client.get("/slow")
    assert resp.status_code == 200
    assert resp.get_json()["lab_only"] is True


@patch("app.requests.get")
def test_lab_fail_returns_500(mock_get):
    mock_get.return_value = Mock(status_code=500, json=lambda: {"error": "injected_failure"})
    client = app_module.app.test_client()
    resp = client.get("/fail")
    assert resp.status_code == 500
    body = resp.get_json()
    assert body["lab_only"] is True
    assert body["error"] == "injected_failure"
