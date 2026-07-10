#!/usr/bin/env python3
"""
Service B: Telemetry Parser
Internal service that validates raw telemetry frames, extracts sensor data,
and forwards parsed data to the Anomaly Detector.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify

# Configuration
SERVICE_NAME = "telemetry-parser"
SERVICE_VERSION = "v2.1.0"
PORT = 3002

# Service discovery
ANOMALY_DETECTOR_URL = os.environ.get("ANOMALY_DETECTOR_URL", "http://anomaly-detector:3003/analyze")
# Base URL of the downstream anomaly detector (strip the /analyze path) so the
# lab /slow and /fail endpoints can propagate a trace to the next service.
ANOMALY_DETECTOR_BASE_URL = ANOMALY_DETECTOR_URL.rsplit("/", 1)[0]

# LAB-ONLY: how long the /slow endpoint sleeps before calling downstream.
LAB_SLOW_SECONDS = float(os.environ.get("LAB_SLOW_SECONDS", "3"))

app = Flask(__name__)
app.start_time = time.time()


class JSONLogFormatter(logging.Formatter):
    """Custom formatter for structured JSON logs."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": SERVICE_NAME,
            "service_version": SERVICE_VERSION,
            "level": record.levelname,
            "event": getattr(record, "event", "unknown"),
            "processing_request_id": getattr(record, "processing_request_id", None),
            "satellite_id": getattr(record, "satellite_id", None),
            "mission_id": getattr(record, "mission_id", None),
            "endpoint": getattr(record, "endpoint", None),
            "method": getattr(record, "method", None),
            "outcome": getattr(record, "outcome", "unknown"),
            "duration_ms": getattr(record, "duration_ms", None),
            "message": record.getMessage()
        }
        # Correlate logs with the active distributed trace (MELT: Logs <-> Traces).
        trace_id = current_trace_id()
        if trace_id:
            log_entry["trace_id"] = trace_id
        # Expose processing_request_id under the generic "request_id" key too.
        if log_entry.get("processing_request_id"):
            log_entry["request_id"] = log_entry["processing_request_id"]
        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        return json.dumps(log_entry)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONLogFormatter())
logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


# ---------------------------------------------------------------------------
# MELT observability layer (Metrics + Traces). Added for the observability lab.
#   - Metrics: Prometheus client exposing http_requests_total,
#     http_request_duration_seconds, http_errors_total, service_up on /metrics.
#   - Traces: OpenTelemetry auto-instrumentation exporting spans to Jaeger (OTLP).
# See docs/architecture.md for the full telemetry flow.
# ---------------------------------------------------------------------------
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the service",
    ["service", "method", "route", "status_code"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["service", "method", "route"],
)
http_errors_total = Counter(
    "http_errors_total",
    "Total HTTP responses that resulted in a 5xx error",
    ["service", "method", "route", "status_code"],
)
service_up = Gauge("service_up", "1 while the service process is running", ["service"])
service_up.labels(service=SERVICE_NAME).set(1)

# OpenTelemetry tracing is best-effort: if the libraries or the Jaeger collector
# are unavailable (e.g. running a unit test or bare local dev), the service still
# boots and simply skips span export.
_tracing_enabled = False
otel_trace = None
try:
    if os.environ.get("OTEL_SDK_DISABLED", "false").lower() != "true":
        from opentelemetry import trace as otel_trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        _otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
        _provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
        _provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=_otlp_endpoint, insecure=True))
        )
        otel_trace.set_tracer_provider(_provider)
        FlaskInstrumentor().instrument_app(app)
        RequestsInstrumentor().instrument()
        _tracing_enabled = True
except Exception as _otel_err:  # pragma: no cover - tracing must never block boot
    print(f"[otel] tracing disabled for {SERVICE_NAME}: {_otel_err}", flush=True)


def current_trace_id():
    """Return the active trace id as a 32-char hex string, or None if untraced."""
    if not _tracing_enabled or otel_trace is None:
        return None
    try:
        ctx = otel_trace.get_current_span().get_span_context()
        if ctx and ctx.is_valid:
            return format(ctx.trace_id, "032x")
    except Exception:
        return None
    return None


@app.before_request
def _obs_start_timer():
    request._obs_start = time.time()


@app.after_request
def _obs_record_metrics(response):
    try:
        route = request.url_rule.rule if request.url_rule else request.path
        if route != "/metrics":
            method = request.method
            status = str(response.status_code)
            elapsed = time.time() - getattr(request, "_obs_start", time.time())
            http_requests_total.labels(SERVICE_NAME, method, route, status).inc()
            http_request_duration_seconds.labels(SERVICE_NAME, method, route).observe(elapsed)
            if response.status_code >= 500:
                http_errors_total.labels(SERVICE_NAME, method, route, status).inc()
    except Exception:  # pragma: no cover - metrics must never break a response
        pass
    return response


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus scrape endpoint."""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


def log_event(event, outcome, processing_request_id=None, satellite_id=None,
              mission_id=None, endpoint=None, method=None, duration_ms=None,
              message="", level=logging.INFO):
    """Helper to create structured log entries."""
    extra = {
        "event": event,
        "outcome": outcome,
        "processing_request_id": processing_request_id,
        "satellite_id": satellite_id,
        "mission_id": mission_id,
        "endpoint": endpoint,
        "method": method,
        "duration_ms": duration_ms
    }
    logger.log(level, message, extra=extra)


def validate_checksum(telemetry_frame):
    """
    Mock checksum validation.
    In production, this would verify CRC or XOR checksum from satellite.
    """
    # Simple mock: if frame has required fields, checksum is "valid"
    required_fields = ["battery_voltage", "solar_panel_temp", "gyro_x", "gyro_y", "gyro_z"]
    return all(field in telemetry_frame for field in required_fields)


def parse_telemetry_frame(telemetry_frame):
    """
    Extract and normalize sensor data from raw telemetry frame.
    """
    parsed = {
        "battery_voltage_v": float(telemetry_frame.get("battery_voltage", 0)),
        "solar_panel_temp_c": float(telemetry_frame.get("solar_panel_temp", 0)),
        "gyroscope": {
            "x": float(telemetry_frame.get("gyro_x", 0)),
            "y": float(telemetry_frame.get("gyro_y", 0)),
            "z": float(telemetry_frame.get("gyro_z", 0))
        },
        "signal_strength": int(telemetry_frame.get("signal_strength_dbm", -999)),
        "downlink_freq_mhz": float(telemetry_frame.get("downlink_frequency", 0))
    }
    return parsed


@app.route("/health", methods=["GET"])
def health_check():
    """Health endpoint for telemetry parser."""
    start_time = time.time()
    duration_ms = int((time.time() - start_time) * 1000)

    log_event(
        event="health_check",
        outcome="success",
        endpoint="/health",
        method="GET",
        duration_ms=duration_ms,
        message="Telemetry parser health check completed"
    )

    return jsonify({
        "service": SERVICE_NAME,
        "status": "operational",
        "parser_version": SERVICE_VERSION,
        "uptime_seconds": int(time.time() - app.start_time)
    }), 200


@app.route("/parse", methods=["POST"])
def parse_telemetry():
    """Receive raw telemetry frame, validate, parse, and forward to anomaly detector."""
    start_time = time.time()

    try:
        payload = request.get_json()
        if not payload:
            log_event(
                event="parse_request",
                outcome="failure",
                endpoint="/parse",
                method="POST",
                message="Invalid JSON payload received",
                level=logging.WARNING
            )
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        processing_request_id = payload.get("processing_request_id", "UNKNOWN")
        satellite_id = payload.get("satellite_id", "UNKNOWN")
        mission_id = payload.get("mission_id", "UNKNOWN")
        telemetry_frame = payload.get("telemetry_frame", {})

        log_event(
            event="parse_request",
            outcome="received",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            mission_id=mission_id,
            endpoint="/parse",
            method="POST",
            message=f"Parsing telemetry frame from {satellite_id}"
        )

        # Validate checksum
        checksum_valid = validate_checksum(telemetry_frame)
        if not checksum_valid:
            log_event(
                event="checksum_validation",
                outcome="failure",
                processing_request_id=processing_request_id,
                satellite_id=satellite_id,
                message="Telemetry frame checksum invalid - missing required fields",
                level=logging.WARNING
            )
            return jsonify({
                "status": "error",
                "processing_request_id": processing_request_id,
                "satellite_id": satellite_id,
                "message": "Invalid telemetry frame - checksum failed"
            }), 400

        log_event(
            event="checksum_validation",
            outcome="success",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            message="Telemetry frame checksum valid"
        )

        # Parse telemetry frame
        parsed_data = parse_telemetry_frame(telemetry_frame)

        log_event(
            event="telemetry_parsed",
            outcome="success",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            message=f"Telemetry parsed: battery={parsed_data['battery_voltage_v']}V, temp={parsed_data['solar_panel_temp_c']}C"
        )

        duration_ms = int((time.time() - start_time) * 1000)

        log_event(
            event="parse_complete",
            outcome="success",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            mission_id=mission_id,
            endpoint="/parse",
            method="POST",
            duration_ms=duration_ms,
            message="Telemetry parsing completed successfully"
        )

        # Forward parsed data to Anomaly Detector (Service C)
        analyze_payload = {
            "processing_request_id": processing_request_id,
            "satellite_id": satellite_id,
            "mission_id": mission_id,
            "parsed_data": parsed_data
        }

        log_event(
            event="forward_to_detector",
            outcome="in_progress",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            message=f"Forwarding to anomaly detector at {ANOMALY_DETECTOR_URL}"
        )

        try:
            detector_response = requests.post(
                ANOMALY_DETECTOR_URL,
                json=analyze_payload,
                timeout=10,
                headers={"X-Request-ID": processing_request_id}
            )
            detector_response.raise_for_status()
            detector_data = detector_response.json()

            log_event(
                event="detector_response_received",
                outcome="success",
                processing_request_id=processing_request_id,
                satellite_id=satellite_id,
                message=f"Detector responded: {detector_data.get('anomaly_status')}"
            )

        except requests.exceptions.RequestException as e:
            log_event(
                event="forward_to_detector",
                outcome="failure",
                processing_request_id=processing_request_id,
                satellite_id=satellite_id,
                message=f"Failed to reach anomaly detector: {str(e)}",
                level=logging.ERROR
            )
            return jsonify({
                "status": "error",
                "processing_request_id": processing_request_id,
                "satellite_id": satellite_id,
                "message": f"Anomaly detector unreachable: {str(e)}"
            }), 502

        return jsonify({
            "status": "parsed",
            "processing_request_id": processing_request_id,
            "satellite_id": satellite_id,
            "parsed_data": parsed_data,
            "checksum_valid": True,
            "parser_version": SERVICE_VERSION
        }), 200

    except Exception as e:
        log_event(
            event="parse_request",
            outcome="failure",
            endpoint="/parse",
            method="POST",
            message=f"Unexpected error during parsing: {str(e)}",
            level=logging.ERROR
        )
        return jsonify({"status": "error", "message": f"Internal error: {str(e)}"}), 500


@app.route("/slow", methods=["GET"])
def lab_slow():
    """
    LAB-ONLY / TEST-ONLY endpoint.
    Sleeps LAB_SLOW_SECONDS then calls the anomaly detector's /slow so a single
    request produces a slow span in BOTH service-b and service-c in Jaeger.
    Do NOT expose in production.
    """
    start_time = time.time()
    time.sleep(LAB_SLOW_SECONDS)
    downstream = None
    try:
        resp = requests.get(f"{ANOMALY_DETECTOR_BASE_URL}/slow", timeout=30)
        downstream = resp.json()
    except requests.exceptions.RequestException as e:
        downstream = {"error": str(e)}
    duration_ms = int((time.time() - start_time) * 1000)
    log_event(
        event="lab_slow",
        outcome="success",
        endpoint="/slow",
        method="GET",
        duration_ms=duration_ms,
        message=f"LAB slow endpoint slept {LAB_SLOW_SECONDS}s and called detector",
        level=logging.WARNING,
    )
    return jsonify({
        "service": SERVICE_NAME,
        "lab_only": True,
        "slept_seconds": LAB_SLOW_SECONDS,
        "downstream": downstream,
    }), 200


@app.route("/fail", methods=["GET"])
def lab_fail():
    """
    LAB-ONLY / TEST-ONLY endpoint.
    Calls the anomaly detector's /fail and propagates a 500 so the error and its
    failed span appear across service-b and service-c. Do NOT expose in production.
    """
    downstream = None
    try:
        resp = requests.get(f"{ANOMALY_DETECTOR_BASE_URL}/fail", timeout=10)
        downstream = resp.json()
    except requests.exceptions.RequestException as e:
        downstream = {"error": str(e)}
    log_event(
        event="lab_fail",
        outcome="failure",
        endpoint="/fail",
        method="GET",
        message="LAB fail endpoint invoked - propagating injected 500 from detector",
        level=logging.ERROR,
    )
    return jsonify({
        "service": SERVICE_NAME,
        "lab_only": True,
        "error": "injected_failure",
        "downstream": downstream,
    }), 500


@app.errorhandler(404)
def not_found(error):
    log_event(
        event="invalid_endpoint",
        outcome="failure",
        endpoint=request.path,
        method=request.method,
        message=f"Invalid endpoint accessed: {request.path}"
    )
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    log_event(
        event="internal_error",
        outcome="failure",
        endpoint=request.path,
        method=request.method,
        message=f"Internal server error: {str(error)}"
    )
    return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == "__main__":
    log_event(
        event="service_startup",
        outcome="success",
        message=f"{SERVICE_NAME} {SERVICE_VERSION} starting on port {PORT}"
    )
    app.run(host="0.0.0.0", port=PORT, threaded=True)
