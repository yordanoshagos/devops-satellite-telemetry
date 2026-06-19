#!/usr/bin/env python3
"""
Service A: Ground Station API
Public-facing entry point for satellite telemetry processing.
Receives telemetry frames, forwards to parser, receives callbacks from anomaly detector.
"""

import os
import sys
import json
import time
import uuid
import logging
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify

# Configuration
SERVICE_NAME = "ground-station-api"
SERVICE_VERSION = "v1.0.0"
GROUND_STATION_ID = "GS-Nairobi-1"
PORT = 3001

# Service discovery - internal services communicate by hostname
TELEMETRY_PARSER_URL = os.environ.get("TELEMETRY_PARSER_URL", "http://telemetry-parser:3002/parse")
ANOMALY_DETECTOR_URL = os.environ.get("ANOMALY_DETECTOR_URL", "http://anomaly-detector:3003/analyze")

app = Flask(__name__)

# In-memory store for tracking requests (in production, use Redis)
request_store = {}


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
            "client_ip": getattr(record, "client_ip", None),
            "outcome": getattr(record, "outcome", "unknown"),
            "duration_ms": getattr(record, "duration_ms", None),
            "message": record.getMessage()
        }
        # Remove None values for cleaner logs
        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        return json.dumps(log_entry)


# Setup structured logging
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONLogFormatter())
logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


def log_event(event, outcome, processing_request_id=None, satellite_id=None, 
              mission_id=None, endpoint=None, method=None, client_ip=None, 
              duration_ms=None, message="", level=logging.INFO):
    """Helper to create structured log entries with extra fields."""
    extra = {
        "event": event,
        "outcome": outcome,
        "processing_request_id": processing_request_id,
        "satellite_id": satellite_id,
        "mission_id": mission_id,
        "endpoint": endpoint,
        "method": method,
        "client_ip": client_ip,
        "duration_ms": duration_ms
    }
    logger.log(level, message, extra=extra)


@app.route("/health", methods=["GET"])
def health_check():
    """Health endpoint - returns operational status and dependency reachability."""
    start_time = time.time()

    # Check dependencies
    dependencies = {}
    try:
        resp = requests.get("http://telemetry-parser:3002/health", timeout=2)
        dependencies["telemetry_parser"] = "reachable" if resp.status_code == 200 else "unhealthy"
    except Exception as e:
        dependencies["telemetry_parser"] = f"unreachable: {str(e)}"

    try:
        resp = requests.get("http://anomaly-detector:3003/health", timeout=2)
        dependencies["anomaly_detector"] = "reachable" if resp.status_code == 200 else "unhealthy"
    except Exception as e:
        dependencies["anomaly_detector"] = f"unreachable: {str(e)}"

    duration_ms = int((time.time() - start_time) * 1000)

    log_event(
        event="health_check",
        outcome="success",
        endpoint="/health",
        method="GET",
        duration_ms=duration_ms,
        message="Health check completed"
    )

    return jsonify({
        "service": SERVICE_NAME,
        "status": "operational",
        "ground_station_id": GROUND_STATION_ID,
        "service_version": SERVICE_VERSION,
        "uptime_seconds": int(time.time() - app.start_time),
        "dependencies": dependencies
    }), 200


@app.route("/telemetry", methods=["POST"])
def receive_telemetry():
    """Receive raw telemetry frame from satellite and initiate processing pipeline."""
    start_time = time.time()
    processing_request_id = f"req-{uuid.uuid4().hex[:12]}"
    client_ip = request.remote_addr

    try:
        payload = request.get_json()
        if not payload:
            log_event(
                event="telemetry_received",
                outcome="failure",
                processing_request_id=processing_request_id,
                endpoint="/telemetry",
                method="POST",
                client_ip=client_ip,
                message="Invalid JSON payload received",
                level=logging.WARNING
            )
            return jsonify({
                "status": "error",
                "processing_request_id": processing_request_id,
                "message": "Invalid JSON payload"
            }), 400

        satellite_id = payload.get("satellite_id", "UNKNOWN")
        mission_id = payload.get("mission_id", "UNKNOWN")

        log_event(
            event="telemetry_received",
            outcome="success",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            mission_id=mission_id,
            endpoint="/telemetry",
            method="POST",
            client_ip=client_ip,
            message=f"Telemetry frame received from {satellite_id}"
        )

        # Store request for callback matching
        request_store[processing_request_id] = {
            "satellite_id": satellite_id,
            "mission_id": mission_id,
            "status": "processing",
            "received_at": datetime.now(timezone.utc).isoformat()
        }

        # Forward to Telemetry Parser (Service B)
        forward_payload = {
            "processing_request_id": processing_request_id,
            "satellite_id": satellite_id,
            "mission_id": mission_id,
            "timestamp": payload.get("timestamp"),
            "telemetry_frame": payload.get("telemetry_frame", {})
        }

        log_event(
            event="forward_to_parser",
            outcome="in_progress",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            message=f"Forwarding to telemetry parser at {TELEMETRY_PARSER_URL}"
        )

        try:
            parser_response = requests.post(
                TELEMETRY_PARSER_URL,
                json=forward_payload,
                timeout=10,
                headers={"X-Request-ID": processing_request_id}
            )
            parser_response.raise_for_status()
            parser_data = parser_response.json()

            log_event(
                event="parser_response_received",
                outcome="success",
                processing_request_id=processing_request_id,
                satellite_id=satellite_id,
                message=f"Parser responded: {parser_data.get('status')}"
            )

        except requests.exceptions.RequestException as e:
            log_event(
                event="forward_to_parser",
                outcome="failure",
                processing_request_id=processing_request_id,
                satellite_id=satellite_id,
                message=f"Failed to reach telemetry parser: {str(e)}",
                level=logging.ERROR
            )
            request_store[processing_request_id]["status"] = "failed"
            return jsonify({
                "status": "error",
                "processing_request_id": processing_request_id,
                "message": f"Telemetry parser unreachable: {str(e)}"
            }), 502

        # Forward parsed data to Anomaly Detector (Service C)
        analyze_payload = {
            "processing_request_id": processing_request_id,
            "satellite_id": satellite_id,
            "mission_id": mission_id,
            "parsed_data": parser_data.get("parsed_data", {})
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
            request_store[processing_request_id]["status"] = "failed"
            return jsonify({
                "status": "error",
                "processing_request_id": processing_request_id,
                "message": f"Anomaly detector unreachable: {str(e)}"
            }), 502

        duration_ms = int((time.time() - start_time) * 1000)

        # Wait for callback from Service C (in this simplified version, we return immediately)
        # In production, this would be async with webhook or polling
        request_store[processing_request_id]["status"] = "awaiting_callback"

        log_event(
            event="telemetry_accepted",
            outcome="success",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            mission_id=mission_id,
            endpoint="/telemetry",
            method="POST",
            client_ip=client_ip,
            duration_ms=duration_ms,
            message=f"Telemetry frame accepted, awaiting anomaly analysis callback"
        )

        return jsonify({
            "status": "accepted",
            "ground_station_id": GROUND_STATION_ID,
            "processing_request_id": processing_request_id,
            "satellite_id": satellite_id,
            "message": "Telemetry frame queued for processing"
        }), 202

    except Exception as e:
        log_event(
            event="telemetry_received",
            outcome="failure",
            processing_request_id=processing_request_id,
            endpoint="/telemetry",
            method="POST",
            client_ip=client_ip,
            message=f"Unexpected error: {str(e)}",
            level=logging.ERROR
        )
        return jsonify({
            "status": "error",
            "processing_request_id": processing_request_id,
            "message": f"Internal error: {str(e)}"
        }), 500


@app.route("/callback", methods=["POST"])
def receive_callback():
    """Receive callback from Anomaly Detector (Service C) with analysis results."""
    start_time = time.time()

    try:
        payload = request.get_json()
        if not payload:
            log_event(
                event="callback_received",
                outcome="failure",
                endpoint="/callback",
                method="POST",
                message="Invalid callback payload",
                level=logging.WARNING
            )
            return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        processing_request_id = payload.get("processing_request_id")
        satellite_id = payload.get("satellite_id", "UNKNOWN")
        anomaly_status = payload.get("anomaly_status", "unknown")
        anomalies = payload.get("anomalies_detected", [])

        if not processing_request_id:
            log_event(
                event="callback_received",
                outcome="failure",
                endpoint="/callback",
                method="POST",
                message="Callback missing processing_request_id",
                level=logging.ERROR
            )
            return jsonify({"status": "error", "message": "Missing processing_request_id"}), 400

        # Update request store
        if processing_request_id in request_store:
            request_store[processing_request_id]["status"] = "completed"
            request_store[processing_request_id]["anomaly_status"] = anomaly_status
            request_store[processing_request_id]["anomalies"] = anomalies
            request_store[processing_request_id]["completed_at"] = datetime.now(timezone.utc).isoformat()

        duration_ms = int((time.time() - start_time) * 1000)

        log_event(
            event="callback_received",
            outcome="success",
            processing_request_id=processing_request_id,
            satellite_id=satellite_id,
            endpoint="/callback",
            method="POST",
            duration_ms=duration_ms,
            message=f"Callback received from anomaly detector: {anomaly_status}, {len(anomalies)} anomalies"
        )

        return jsonify({
            "status": "acknowledged",
            "ground_station_id": GROUND_STATION_ID,
            "processing_request_id": processing_request_id,
            "anomaly_status": anomaly_status
        }), 200

    except Exception as e:
        log_event(
            event="callback_received",
            outcome="failure",
            endpoint="/callback",
            method="POST",
            message=f"Unexpected error processing callback: {str(e)}",
            level=logging.ERROR
        )
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/status/<processing_request_id>", methods=["GET"])
def get_request_status(processing_request_id):
    """Get the status of a processing request."""
    if processing_request_id not in request_store:
        log_event(
            event="status_check",
            outcome="failure",
            processing_request_id=processing_request_id,
            endpoint=f"/status/{processing_request_id}",
            method="GET",
            message="Request ID not found"
        )
        return jsonify({"status": "error", "message": "Request ID not found"}), 404

    data = request_store[processing_request_id]
    log_event(
        event="status_check",
        outcome="success",
        processing_request_id=processing_request_id,
        satellite_id=data.get("satellite_id"),
        endpoint=f"/status/{processing_request_id}",
        method="GET",
        message=f"Status check: {data.get('status')}"
    )

    return jsonify({
        "processing_request_id": processing_request_id,
        "status": data.get("status"),
        "satellite_id": data.get("satellite_id"),
        "mission_id": data.get("mission_id"),
        "anomaly_status": data.get("anomaly_status"),
        "anomalies_detected": data.get("anomalies", []),
        "received_at": data.get("received_at"),
        "completed_at": data.get("completed_at")
    }), 200


@app.errorhandler(404)
def not_found(error):
    log_event(
        event="invalid_endpoint",
        outcome="failure",
        endpoint=request.path,
        method=request.method,
        client_ip=request.remote_addr,
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
        client_ip=request.remote_addr,
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
