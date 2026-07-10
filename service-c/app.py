#!/usr/bin/env python3
"""
Service C: Anomaly Detector
Internal service that analyzes parsed telemetry data against mission thresholds,
detects anomalies, and calls back to the Ground Station API with results.
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
SERVICE_NAME = "anomaly-detector"
SERVICE_VERSION = "v1.3.0"
PORT = 3003

# Service discovery - callback to Ground Station API
GROUND_STATION_CALLBACK_URL = os.environ.get(
    "GROUND_STATION_CALLBACK_URL", 
    "http://ground-station-api:3001/callback"
)

# LAB-ONLY: how long the /slow endpoint sleeps to simulate latency.
LAB_SLOW_SECONDS = float(os.environ.get("LAB_SLOW_SECONDS", "3"))

# Mission thresholds for anomaly detection
THRESHOLDS = {
    "battery_voltage_v": {"min": 12.0, "max": 16.0, "critical_low": 11.0},
    "solar_panel_temp_c": {"min": -40.0, "max": 80.0, "critical_high": 90.0},
    "signal_strength": {"min": -120, "max": -50, "critical_low": -130},
    "gyroscope": {"max_deviation": 2.0}  # Max deviation from zero for any axis
}

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
        # Expose processing_request_id under the generic "request_id" key too, so
        # log tooling that expects request_id (per the PRD) can correlate as well.
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


def check_anomalies(parsed_data):
    """
    Analyze parsed telemetry data against mission thresholds.
    Returns anomaly status and list of detected anomalies.
    """
    anomalies = []

    # Check battery voltage
    battery_v = parsed_data.get("battery_voltage_v", 0)
    battery_thresholds = THRESHOLDS["battery_voltage_v"]
    if battery_v < battery_thresholds["critical_low"]:
        anomalies.append({
            "sensor": "battery_voltage_v",
            "severity": "critical",
            "value": battery_v,
            "threshold_min": battery_thresholds["min"],
            "threshold_max": battery_thresholds["max"],
            "message": f"Battery voltage critically low: {battery_v}V (minimum: {battery_thresholds['min']}V)"
        })
    elif battery_v < battery_thresholds["min"]:
        anomalies.append({
            "sensor": "battery_voltage_v",
            "severity": "warning",
            "value": battery_v,
            "threshold_min": battery_thresholds["min"],
            "threshold_max": battery_thresholds["max"],
            "message": f"Battery voltage below safe threshold: {battery_v}V"
        })
    elif battery_v > battery_thresholds["max"]:
        anomalies.append({
            "sensor": "battery_voltage_v",
            "severity": "warning",
            "value": battery_v,
            "threshold_min": battery_thresholds["min"],
            "threshold_max": battery_thresholds["max"],
            "message": f"Battery voltage above safe threshold: {battery_v}V"
        })

    # Check solar panel temperature
    solar_temp = parsed_data.get("solar_panel_temp_c", 0)
    solar_thresholds = THRESHOLDS["solar_panel_temp_c"]
    if solar_temp > solar_thresholds["critical_high"]:
        anomalies.append({
            "sensor": "solar_panel_temp_c",
            "severity": "critical",
            "value": solar_temp,
            "threshold_min": solar_thresholds["min"],
            "threshold_max": solar_thresholds["max"],
            "message": f"Solar panel temperature critically high: {solar_temp}C (maximum: {solar_thresholds['max']}C)"
        })
    elif solar_temp > solar_thresholds["max"]:
        anomalies.append({
            "sensor": "solar_panel_temp_c",
            "severity": "warning",
            "value": solar_temp,
            "threshold_min": solar_thresholds["min"],
            "threshold_max": solar_thresholds["max"],
            "message": f"Solar panel temperature above safe threshold: {solar_temp}C"
        })
    elif solar_temp < solar_thresholds["min"]:
        anomalies.append({
            "sensor": "solar_panel_temp_c",
            "severity": "warning",
            "value": solar_temp,
            "threshold_min": solar_thresholds["min"],
            "threshold_max": solar_thresholds["max"],
            "message": f"Solar panel temperature below safe threshold: {solar_temp}C"
        })

    # Check signal strength
    signal = parsed_data.get("signal_strength", -999)
    signal_thresholds = THRESHOLDS["signal_strength"]
    if signal < signal_thresholds["critical_low"]:
        anomalies.append({
            "sensor": "signal_strength",
            "severity": "critical",
            "value": signal,
            "threshold_min": signal_thresholds["min"],
            "threshold_max": signal_thresholds["max"],
            "message": f"Signal strength critically weak: {signal} dBm"
        })
    elif signal < signal_thresholds["min"]:
        anomalies.append({
            "sensor": "signal_strength",
            "severity": "warning",
            "value": signal,
            "threshold_min": signal_thresholds["min"],
            "threshold_max": signal_thresholds["max"],
            "message": f"Signal strength below acceptable: {signal} dBm"
        })

    # Check gyroscope stability
    gyro = parsed_data.get("gyroscope", {})
    max_deviation = THRESHOLDS["gyroscope"]["max_deviation"]
    for axis in ["x", "y", "z"]:
        value = abs(gyro.get(axis, 0))
        if value > max_deviation:
            anomalies.append({
                "sensor": f"gyroscope_{axis}",
                "severity": "warning",
                "value": gyro.get(axis, 0),
                "threshold_max": max_deviation,
                "message": f"Gyroscope {axis}-axis deviation high: {gyro.get(axis, 0)} (max: {max_deviation})"
            })

    # Determine overall anomaly status
    if any(a["severity"] == "critical" for a in anomalies):
        anomaly_status = "critical"
    elif anomalies:
        anomaly_status = "warning"
    else:
        anomaly_status = "nominal"

    return anomaly_status, anomalies


@app.route("/health", methods=["GET"])
def health_check():
    """Health endpoint for anomaly detector."""
    start_time = time.time()
    duration_ms = int((time.time() - start_time) * 1000)

    log_event(
        event="health_check",
        outcome="success",
        endpoint="/health",
        method="GET",
        duration_ms=duration_ms,
        message="Anomaly detector health check completed"
    )

    return jsonify({
        "service": SERVICE_NAME,
        "status": "operational",
        "detector_version": SERVICE_VERSION,
        "threshold_rules_loaded": len(THRESHOLDS),
        "uptime_seconds": int(time.time() - app.start_time)
    }), 200


@app.route("/analyze", methods=["POST"])
def analyze_telemetry():
    """Receive parsed telemetry, run anomaly detection, and callback to Ground Station."""
    start_time = time.time()

    try:
        payload = request.get_json()
        if not payload:
            log_event(
                event="analyze_request",
                outcome="failure",
                endpoint="/analyze",
                method="POST",
                message="Invalid JSON payload received",
                level=logging.WARNING
            )
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        # Get the request ID from the incoming header if present
        incoming_request_id = request.headers.get("X-Request-ID")
        if incoming_request_id:
            processing_request_id = incoming_request_id
        else:
            processing_request_id = payload.get("processing_request_id", "UNKNOWN")
        satellite_id = payload.get("satellite_id", "UNKNOWN")
        mission_id = payload.get("mission_id", "UNKNOWN")
        parsed_data = payload.get("parsed_data", {})

        log_event(
            event="analyze_request",
            outcome="received",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            mission_id=mission_id,
            endpoint="/analyze",
            method="POST",
            message=f"Analyzing telemetry from {satellite_id}"
        )

        # Run anomaly detection
        anomaly_status, anomalies = check_anomalies(parsed_data)

        log_event(
            event="anomaly_detection",
            outcome="complete",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            message=f"Anomaly detection complete: {anomaly_status}, {len(anomalies)} anomalies detected"
        )

        # Build threshold check results for response
        thresholds_checked = {}
        for sensor, thresholds in THRESHOLDS.items():
            if sensor == "gyroscope":
                gyro = parsed_data.get("gyroscope", {})
                max_dev = max(abs(gyro.get(axis, 0)) for axis in ["x", "y", "z"])
                thresholds_checked[sensor] = {
                    "max_deviation": thresholds["max_deviation"],
                    "actual": max_dev,
                    "status": "nominal" if max_dev <= thresholds["max_deviation"] else "warning"
                }
            else:
                value = parsed_data.get(sensor, 0)
                status = "nominal"
                if value < thresholds.get("min", float('-inf')):
                    status = "warning"
                if value > thresholds.get("max", float('inf')):
                    status = "warning"
                thresholds_checked[sensor] = {
                    "min": thresholds.get("min"),
                    "max": thresholds.get("max"),
                    "actual": value,
                    "status": status
                }

        # Send callback to Ground Station API (Service A)
        callback_payload = {
            "processing_request_id": processing_request_id,
            "satellite_id": satellite_id,
            "mission_id": mission_id,
            "anomaly_status": anomaly_status,
            "anomalies_detected": anomalies,
            "thresholds_checked": thresholds_checked,
            "processing_timestamp": datetime.now(timezone.utc).isoformat(),
            "detector_version": SERVICE_VERSION
        }

        log_event(
            event="callback_initiated",
            outcome="in_progress",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            message=f"Sending callback to Ground Station at {GROUND_STATION_CALLBACK_URL}"
        )

        try:
            callback_response = requests.post(
                GROUND_STATION_CALLBACK_URL,
                json=callback_payload,
                timeout=10,
                headers={"X-Request-ID": processing_request_id}
            )
            callback_response.raise_for_status()

            log_event(
                event="callback_sent",
                outcome="success",
                processing_request_id=processing_request_id,
                satellite_id=satellite_id,
                message=f"Callback acknowledged by Ground Station: {callback_response.status_code}"
            )

        except requests.exceptions.RequestException as e:
            log_event(
                event="callback_sent",
                outcome="failure",
                processing_request_id=processing_request_id,
                satellite_id=satellite_id,
                message=f"Failed to send callback to Ground Station: {str(e)}",
                level=logging.ERROR
            )
            # Still return the analysis result even if callback fails

        duration_ms = int((time.time() - start_time) * 1000)

        log_event(
            event="analyze_complete",
            outcome="success",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            mission_id=mission_id,
            endpoint="/analyze",
            method="POST",
            duration_ms=duration_ms,
            message=f"Analysis complete for {satellite_id}: {anomaly_status}"
        )

        return jsonify({
            "status": "analyzed",
            "processing_request_id": processing_request_id,
            "satellite_id": satellite_id,
            "anomaly_status": anomaly_status,
            "anomalies_detected": anomalies,
            "thresholds_checked": thresholds_checked,
            "detector_version": SERVICE_VERSION
        }), 200

    except Exception as e:
        log_event(
            event="analyze_request",
            outcome="failure",
            endpoint="/analyze",
            method="POST",
            message=f"Unexpected error during analysis: {str(e)}",
            level=logging.ERROR
        )
        return jsonify({"status": "error", "message": f"Internal error: {str(e)}"}), 500


@app.route("/slow", methods=["GET"])
def lab_slow():
    """
    LAB-ONLY / TEST-ONLY endpoint.
    Sleeps for LAB_SLOW_SECONDS to simulate a slow dependency at the deepest
    point of the pipeline. Used to prove high-latency alerts, slow spans in
    Jaeger, and degraded p95 in the benchmark report. Do NOT expose in prod.
    """
    start_time = time.time()
    time.sleep(LAB_SLOW_SECONDS)
    duration_ms = int((time.time() - start_time) * 1000)
    log_event(
        event="lab_slow",
        outcome="success",
        endpoint="/slow",
        method="GET",
        duration_ms=duration_ms,
        message=f"LAB slow endpoint slept {LAB_SLOW_SECONDS}s",
        level=logging.WARNING,
    )
    return jsonify({
        "service": SERVICE_NAME,
        "lab_only": True,
        "slept_seconds": LAB_SLOW_SECONDS,
        "detector_version": SERVICE_VERSION,
    }), 200


@app.route("/fail", methods=["GET"])
def lab_fail():
    """
    LAB-ONLY / TEST-ONLY endpoint.
    Always returns HTTP 500 so we can drive http_errors_total up, trip the
    high-error-rate alert, and show a failed span in Jaeger. Do NOT expose in prod.
    """
    log_event(
        event="lab_fail",
        outcome="failure",
        endpoint="/fail",
        method="GET",
        message="LAB fail endpoint invoked - returning injected 500",
        level=logging.ERROR,
    )
    return jsonify({
        "service": SERVICE_NAME,
        "lab_only": True,
        "error": "injected_failure",
        "message": "Simulated failure for observability testing",
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