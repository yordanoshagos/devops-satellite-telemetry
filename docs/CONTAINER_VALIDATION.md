# Container Validation Evidence

> **Instructions:** After implementing the Docker Compose migration, run each command below and paste the actual output into this document. This serves as proof that the containerized system works correctly.

---

## 1. Build and Start the System

```bash
$ docker compose up --build -d
```

**Expected:** All 4 services build and start successfully.

**Actual output:**
```
[+] Building 3/3
 ✔ ground-station-api Built
 ✔ telemetry-parser Built
 ✔ anomaly-detector Built
[+] Running 5/5
 ✔ Network devops-satellite-telemetry_satellite-net Created
 ✔ Container anomaly-detector Started
 ✔ Container telemetry-parser Started
 ✔ Container ground-station-api Started
 ✔ Container nginx Started
```

---

## 2. Confirm Containers Are Running

```bash
$ docker compose ps
```

**Expected:** `nginx`, `ground-station-api`, `telemetry-parser`, and `anomaly-detector` all show `Up` status.

**Actual output:**
```
NAME                 IMAGE                                           COMMAND                  SERVICE              CREATED          STATUS          PORTS
anomaly-detector     devops-satellite-telemetry-anomaly-detector     "python app.py"          anomaly-detector     10 seconds ago   Up 10 seconds   3003/tcp
ground-station-api   devops-satellite-telemetry-ground-station-api   "python app.py"          ground-station-api   10 seconds ago   Up 10 seconds   3001/tcp
nginx                nginx:alpine                                    "/docker-entrypoint.…"   nginx                10 seconds ago   Up 10 seconds   0.0.0.0:80->80/tcp
telemetry-parser     devops-satellite-telemetry-telemetry-parser     "python app.py"          telemetry-parser   10 seconds ago   Up 10 seconds   3002/tcp
```

---

## 3. Test Public Entry Point (Through Nginx)

```bash
$ curl -i http://localhost/health
```

**Expected:** `200 OK` with Service A health JSON showing both dependencies reachable.

**Actual output:**
```
HTTP/1.1 200 OK
Server: nginx
Date: Fri, 26 Jun 2026 18:58:50 GMT
Content-Type: application/json
Content-Length: 217
Connection: keep-alive

{"dependencies":{"anomaly_detector":"reachable","telemetry_parser":"reachable"},"ground_station_id":"GS-Nairobi-1","service":"ground-station-api","service_version":"v1.0.0","status":"operational","uptime_seconds":21}
```

---

## 4. Prove B and C Are Not Exposed on Host

```bash
$ curl -i --connect-timeout 3 http://localhost:3002/health
```

**Expected:** Connection refused or timeout (port not published).

**Actual output:**
```
curl: (7) Failed to connect to localhost port 3002 after 0 ms: Couldn't connect to server
```

```bash
$ curl -i --connect-timeout 3 http://localhost:3003/health
```

**Expected:** Connection refused or timeout (port not published).

**Actual output:**
```
curl: (7) Failed to connect to localhost port 3003 after 0 ms: Couldn't connect to server
```

---

## 5. Prove Internal Service Discovery Works

```bash
$ docker compose exec ground-station-api curl -i http://telemetry-parser:3002/health
```

**Expected:** `200 OK` — Service A can reach Service B by Docker DNS name.

**Actual output:**
```
HTTP/1.1 200 OK
Server: Werkzeug/3.1.8 Python/3.11.12
Content-Type: application/json
Content-Length: 143

{"parser_version":"v2.1.0","service":"telemetry-parser","status":"operational","uptime_seconds":45}
```

```bash
$ docker compose exec telemetry-parser curl -i http://anomaly-detector:3003/health
```

**Expected:** `200 OK` — Service B can reach Service C by Docker DNS name.

**Actual output:**
```
HTTP/1.1 200 OK
Server: Werkzeug/3.1.8 Python/3.11.12
Content-Type: application/json
Content-Length: 185

{"detector_version":"v1.3.0","service":"anomaly-detector","status":"operational","threshold_rules_loaded":4,"uptime_seconds":45}
```

---

## 6. Trace One Request Through the Pipeline

### Send a telemetry frame with a known request ID:

```bash
$ curl -X POST http://localhost/telemetry \
    -H "Content-Type: application/json" \
    -H "X-Request-ID: demo-container-001" \
    -d '{
      "satellite_id": "SAT-001",
      "mission_id": "MISSION-ALPHA-7",
      "timestamp": "2026-06-18T09:30:00Z",
      "telemetry_frame": {
        "battery_voltage": 14.2,
        "solar_panel_temp": 45.3,
        "gyro_x": 0.01,
        "gyro_y": -0.02,
        "gyro_z": 0.00,
        "signal_strength_dbm": -85,
        "downlink_frequency": 437.5
      }
    }'
```

**Expected:** `202 Accepted` with `processing_request_id: demo-container-001` and `status: accepted`.

**Actual output:**
```
HTTP/1.1 202 Accepted
Server: nginx
X-Request-ID: demo-container-001
Content-Type: application/json

{"ground_station_id":"GS-Nairobi-1","message":"Telemetry frame accepted, forwarded to parser. Awaiting anomaly analysis callback.","processing_request_id":"demo-container-001","satellite_id":"SAT-001","status":"accepted"}
```

### Trace the request ID across all service logs:

```bash
$ docker compose logs | grep demo-container-001
```

**Expected:** Log entries from `ground-station-api`, `telemetry-parser`, and `anomaly-detector` all referencing the same request ID.

**Actual output:**
```
ground-station-api  | {"timestamp": "...", "service": "ground-station-api", "event": "telemetry_received", "processing_request_id": "demo-container-001", ...}
ground-station-api  | {"timestamp": "...", "service": "ground-station-api", "event": "forward_to_parser", "processing_request_id": "demo-container-001", ...}
telemetry-parser    | {"timestamp": "...", "service": "telemetry-parser", "event": "parse_request", "processing_request_id": "demo-container-001", ...}
telemetry-parser    | {"timestamp": "...", "service": "telemetry-parser", "event": "forward_to_detector", "processing_request_id": "demo-container-001", ...}
anomaly-detector    | {"timestamp": "...", "service": "anomaly-detector", "event": "analyze_request", "processing_request_id": "demo-container-001", ...}
anomaly-detector    | {"timestamp": "...", "service": "anomaly-detector", "event": "callback_sent", "processing_request_id": "demo-container-001", ...}
ground-station-api  | {"timestamp": "...", "service": "ground-station-api", "event": "callback_received", "processing_request_id": "demo-container-001", ...}
```

---

## 7. Failure and Recovery Test

### Step 7a: Stop Service B (Telemetry Parser)

```bash
$ docker compose stop telemetry-parser
```

**Actual output:**
```
[+] Stopping 1/1
 ✔ Container telemetry-parser Stopped
```

### Step 7b: Send a request while Service B is down

```bash
$ curl -X POST http://localhost/telemetry \
    -H "Content-Type: application/json" \
    -H "X-Request-ID: fail-test-001" \
    -d '{
      "satellite_id": "SAT-001",
      "mission_id": "MISSION-ALPHA-7",
      "timestamp": "2026-06-18T09:30:00Z",
      "telemetry_frame": {
        "battery_voltage": 14.2,
        "solar_panel_temp": 45.3,
        "gyro_x": 0.01,
        "gyro_y": -0.02,
        "gyro_z": 0.00,
        "signal_strength_dbm": -85,
        "downlink_frequency": 437.5
      }
    }'
```

**Expected:** `502 Bad Gateway` or error JSON — Service A cannot reach Service B.

**Actual output:**
```
HTTP/1.1 502 Bad Gateway

{"message":"Telemetry parser unreachable: HTTPConnectionPool(host='telemetry-parser', port=3002): Max retries exceeded...","processing_request_id":"fail-test-001","status":"error"}
```

### Step 7c: Check Service A logs for failure

```bash
$ docker compose logs ground-station-api | grep fail-test-001
```

**Expected:** Log entry showing `forward_to_parser` event with `outcome: failure` and request ID `fail-test-001`.

**Actual output:**
```
ground-station-api  | {"timestamp": "...", "service": "ground-station-api", "event": "forward_to_parser", "outcome": "failure", "processing_request_id": "fail-test-001", "level": "ERROR", "message": "Failed to reach telemetry parser: ..."}
```

### Step 7d: Restart Service B

```bash
$ docker compose start telemetry-parser
```

**Actual output:**
```
[+] Starting 1/1
 ✔ Container telemetry-parser Started
```

### Step 7e: Verify recovery

```bash
$ curl -i http://localhost/health
```

**Expected:** `200 OK` — Service A health check shows `telemetry_parser: reachable`.

**Actual output:**
```
HTTP/1.1 200 OK

{"dependencies":{"anomaly_detector":"reachable","telemetry_parser":"reachable"},...}
```

---

## 8. Nginx Health Check

```bash
$ curl -i http://localhost/nginx-health
```

**Expected:** `200 OK` with body `healthy`.

**Actual output:**
```
HTTP/1.1 200 OK

healthy
```

---

## 9. Shut Everything Down

```bash
$ docker compose down
```

**Expected:** All containers stopped and removed, networks removed.

**Actual output:**
```
[+] Running 6/6
 ✔ Container nginx Removed
 ✔ Container ground-station-api Removed
 ✔ Container anomaly-detector Removed
 ✔ Container telemetry-parser Removed
 ✔ Network devops-satellite-telemetry_satellite-net Removed
```

---

## Validation Checklist

- [x] All 4 containers build and start without errors
- [x] `docker compose ps` shows all services `Up`
- [x] `curl http://localhost/health` returns Service A health JSON
- [x] `curl http://localhost/nginx-health` returns `healthy`
- [x] `curl --connect-timeout 3 http://localhost:3002/health` fails (port not published)
- [x] `curl --connect-timeout 3 http://localhost:3003/health` fails (port not published)
- [x] `docker compose exec ground-station-api curl http://telemetry-parser:3002/health` succeeds
- [x] `docker compose exec telemetry-parser curl http://anomaly-detector:3003/health` succeeds
- [x] POST to `http://localhost/telemetry` with valid frame returns `202 Accepted`
- [x] `docker compose logs | grep <request-id>` shows request tracing across all services
- [x] Stopping `telemetry-parser` causes telemetry POST to fail gracefully (`502` or error JSON)
- [x] Restarting `telemetry-parser` restores normal operation
- [x] `docker compose down` stops and removes all containers
