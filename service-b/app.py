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

app = Flask(__name__)


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
        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        return json.dumps(log_entry)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONLogFormatter())
logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


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
    app.start_time = time.time()
    log_event(
        event="service_startup",
        outcome="success",
        message=f"{SERVICE_NAME} {SERVICE_VERSION} starting on port {PORT}"
    )
    app.run(host="0.0.0.0", port=PORT, threaded=True)
