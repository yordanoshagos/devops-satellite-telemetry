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
[paste output here]
```

---

## 2. Confirm Containers Are Running

```bash
$ docker compose ps
```

**Expected:** `nginx`, `ground-station-api`, `telemetry-parser`, and `anomaly-detector` all show `Up` status.

**Actual output:**
```
[paste output here]
```

---

## 3. Test Public Entry Point (Through Nginx)

```bash
$ curl -i http://localhost/health
```

**Expected:** `200 OK` with Service A health JSON.

**Actual output:**
```
[paste output here]
```

---

## 4. Prove B and C Are Not Exposed on Host

```bash
$ curl -i --connect-timeout 3 http://localhost:3002/health
```

**Expected:** Connection refused or timeout (port not published).

**Actual output:**
```
[paste output here]
```

```bash
$ curl -i --connect-timeout 3 http://localhost:3003/health
```

**Expected:** Connection refused or timeout (port not published).

**Actual output:**
```
[paste output here]
```

---

## 5. Prove Internal Service Discovery Works

```bash
$ docker compose exec ground-station-api curl -i http://telemetry-parser:3002/health
```

**Expected:** `200 OK` — Service A can reach Service B by Docker DNS name.

**Actual output:**
```
[paste output here]
```

```bash
$ docker compose exec telemetry-parser curl -i http://anomaly-detector:3003/health
```

**Expected:** `200 OK` — Service B can reach Service C by Docker DNS name.

**Actual output:**
```
[paste output here]
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

**Expected:** `202 Accepted` with `processing_request_id` and `status: accepted`.

**Actual output:**
```
[paste output here]
```

### Trace the request ID across all service logs:

```bash
$ docker compose logs | grep demo-container-001
```

**Expected:** Log entries from `ground-station-api`, `telemetry-parser`, and `anomaly-detector` all referencing the same request ID.

**Actual output:**
```
[paste output here]
```

---

## 7. Failure and Recovery Test

### Step 7a: Stop Service B (Telemetry Parser)

```bash
$ docker compose stop telemetry-parser
```

**Actual output:**
```
[paste output here]
```

### Step 7b: Send a request while Service B is down

```bash
$ curl -X POST http://localhost/telemetry \
    -H "Content-Type: application/json" \
    -H "X-Request-ID: fail-service-b-001" \
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
[paste output here]
```

### Step 7c: Check Service A logs for failure

```bash
$ docker compose logs ground-station-api
```

**Expected:** Log entry showing `forward_to_parser` event with `outcome: failure` and request ID `fail-service-b-001`.

**Actual output:**
```
[paste output here]
```

### Step 7d: Restart Service B

```bash
$ docker compose start telemetry-parser
```

**Actual output:**
```
[paste output here]
```

### Step 7e: Verify recovery

```bash
$ curl -i http://localhost/health
```

**Expected:** `200 OK` — Service A health check shows `telemetry_parser: reachable`.

**Actual output:**
```
[paste output here]
```

---

## 8. Nginx Health Check

```bash
$ curl -i http://localhost/nginx-health
```

**Expected:** `200 OK` with body `healthy`.

**Actual output:**
```
[paste output here]
```

---

## 9. Shut Everything Down

```bash
$ docker compose down
```

**Expected:** All containers stopped and removed, networks removed.

**Actual output:**
```
[paste output here]
```

---

## Validation Checklist

- [ ] All 4 containers build and start without errors
- [ ] `docker compose ps` shows all services `Up`
- [ ] `curl http://localhost/health` returns Service A health JSON
- [ ] `curl http://localhost/nginx-health` returns `healthy`
- [ ] `curl --connect-timeout 3 http://localhost:3002/health` fails (port not published)
- [ ] `curl --connect-timeout 3 http://localhost:3003/health` fails (port not published)
- [ ] POST to `http://localhost/telemetry` with valid frame returns `202 Accepted`
- [ ] `docker compose logs` shows request tracing across all services with same `processing_request_id`
- [ ] Stopping `telemetry-parser` causes telemetry POST to fail gracefully (`502` or error JSON)
- [ ] Restarting `telemetry-parser` restores normal operation
- [ ] `docker compose down` stops and removes all containers
