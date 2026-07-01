# 🛰️ Satellite Telemetry Processing Pipeline

A production-style microservices pipeline that simulates a satellite ground station receiving, parsing, and analyzing telemetry data. Built with Flask, Nginx, and systemd for a DevOps/Systems Engineering assignment.

---

## ⚠️ IMPORTANT: Run `install.sh` Before Testing (VM Deployment)

This project requires systemd services and `/etc/hosts` configuration. **You MUST run the install script before testing any endpoints.**

```bash
# After cloning, run this FIRST:
sudo bash install.sh
```

**Skipping this step will cause `NameResolutionError` when services try to communicate.**

> **Prefer Docker Compose?** See [Running with Docker Compose](#-running-with-docker-compose) for a containerized alternative that requires no `install.sh` or `/etc/hosts` setup.

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start (Run Locally)](#quick-start-run-locally)
- [Full Deployment (Production)](#full-deployment-production)
- [Running with Docker Compose](#-running-with-docker-compose)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Team](#team)

---

## Architecture Overview

```
Internet User
      ↓
   Nginx (Port 80) — Public Gateway
      ↓
Service A: Ground Station API (Port 3001)
      ↓
Service B: Telemetry Parser (Port 3002)
      ↓
Service C: Anomaly Detector (Port 3003)
      ↓
Service A: Ground Station API (Port 3001) — Callback
      ↓
   User receives: "Telemetry processed, status: nominal"
```

| Service | Role | Port | Visibility |
|---------|------|------|------------|
| **Service A** | Ground Station API — public entry point | 3001 | Public via Nginx (80) |
| **Service B** | Telemetry Parser — validates & parses frames | 3002 | Internal only |
| **Service C** | Anomaly Detector — checks thresholds & callbacks | 3003 | Internal only |

**Security:** Services B and C are blocked from external access by `ufw`/`iptables`. Only Nginx (port 80) is public.

---

## Quick Start (Run Locally)

> ⚠️ **Prerequisites:** Python 3.10+, `curl`, Linux/macOS terminal

### 1. Clone the Repository

```bash
git clone https://github.com/yordanoshagos/devops-satellite-telemetry.git
cd devops-satellite-telemetry
```

### 1.5 Add Service Discovery Hostnames (Required for Local Development)

Services communicate using hostnames, not hardcoded IPs. Add these to `/etc/hosts`:

```bash
sudo tee -a /etc/hosts << 'EOF'
127.0.0.1 telemetry-parser
127.0.0.1 anomaly-detector
127.0.0.1 ground-station-api
EOF
```

**Why this matters:** When Service A calls `http://telemetry-parser:3002/parse`, your system needs to know that `telemetry-parser` means `localhost` (127.0.0.1). In production, `install.sh` handles this automatically. For local development, you must add it manually.

### 2. Run Service A (Ground Station API)

Open **Terminal 1**:

```bash
cd service-a

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the service
python app.py
```

Service A is now running on `http://localhost:3001`

**Test it:**

```bash
# In a new terminal (Terminal 2)
curl http://localhost:3001/health
```

Expected response:
```json
{"service":"ground-station-api","status":"operational","ground_station_id":"GS-Nairobi-1","service_version":"v1.0.0","uptime_seconds":0}
```

### 3. Run Service B (Telemetry Parser)

Open **Terminal 3**:

```bash
cd service-b

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Service B is now running on `http://localhost:3002`

**Test it:**

```bash
# In Terminal 2
curl http://localhost:3002/health
```

### 4. Run Service C (Anomaly Detector)

Open **Terminal 4**:

```bash
cd service-c

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Service C is now running on `http://localhost:3003`

**Test it:**

```bash
# In Terminal 2
curl http://localhost:3003/health
```

### 5. Test the Full Pipeline

With all 3 services running, send a telemetry frame:

```bash
# In Terminal 2
curl -X POST http://localhost:3001/telemetry \
  -H "Content-Type: application/json" \
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

Expected response:
```json
{"status":"accepted","ground_station_id":"GS-Nairobi-1","processing_request_id":"req-...","satellite_id":"SAT-001","message":"Telemetry frame queued for processing"}
```

### 6. Stop Everything

Press `Ctrl+C` in each terminal (1, 3, 4) to stop the services.

---

## Full Deployment (Production)

Deploy all services as systemd services on a Linux VM with Nginx and firewall.

### Prerequisites

- Ubuntu 22.04+ VM
- Root or sudo access
- Git

### 1. Clone on the VM

```bash
cd /opt
sudo git clone https://github.com/yordanoshagos/devops-satellite-telemetry.git
sudo chown -R $USER:$USER /opt/devops-satellite-telemetry
```

### 2. Run the Install Script

```bash
cd /opt/devops-satellite-telemetry
sudo bash install.sh
```

This will:
- Create service users (`groundstation`, `telemetry`, `anomaly`)
- Install Python dependencies in virtual environments
- Configure Nginx reverse proxy
- Set up firewall rules (port 80 public, 3002/3003 blocked)
- Register and start systemd services
- Add service discovery hostnames to `/etc/hosts`
- **Add hostnames to cloud-init template** (if cloud-init is installed) for reboot persistence
- **Implement readiness gate**: Service A polls B and C health endpoints before starting

> **Note on Reboot Persistence:** On cloud VMs with `cloud-init`, `/etc/hosts` is overwritten on every boot. The `install.sh` script detects this and also adds entries to `/etc/cloud/templates/hosts.debian.tmpl` so your service discovery survives reboots.

> **Note on Readiness Gate:** Service A's systemd unit includes an `ExecStartPre` script that polls Service B and C health endpoints up to 30 times (60 seconds total) before starting. This ensures Service A never accepts requests until its dependencies are actually ready.

### 3. Verify Deployment

```bash
# Check all services are running
sudo systemctl status telemetry-parser anomaly-detector ground-station-api

# Test health endpoint through Nginx
curl http://localhost/health

# Test the full pipeline
curl -X POST http://localhost/telemetry \
  -H "Content-Type: application/json" \
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

### 4. View Logs

```bash
# Watch live logs from all services
sudo journalctl -u ground-station-api -u telemetry-parser -u anomaly-detector -f

# Search logs for a specific request ID
sudo journalctl -u ground-station-api -u telemetry-parser -u anomaly-detector --since "10 minutes ago" | grep "req-XXXXXX"
```

### 5. Manage Services

```bash
# Restart a service
sudo systemctl restart telemetry-parser

# Stop a service
sudo systemctl stop telemetry-parser

# Start a service
sudo systemctl start telemetry-parser

# Enable auto-start on boot
sudo systemctl enable telemetry-parser

# Disable auto-start
sudo systemctl disable telemetry-parser
```

---

## API Reference

## 🐳 Running with Docker Compose

A containerized alternative to the VM/systemd deployment. No `install.sh`, `/etc/hosts`, or firewall configuration is required.

### Docker Compose Command

Use the appropriate command for your Docker installation:

- **Docker Compose v2** (built into Docker CLI): `docker compose`
- **Docker Compose v1** (standalone Python package): `docker-compose`

In the examples below, replace `<compose>` with the appropriate command for your system.

Example:

```bash
<compose> up --build -d
<compose> ps
<compose> logs ground-station-api
<compose> restart ground-station-api
```

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+

### Start the System
```bash
# Build and start all services
<compose> up --build -d

# Verify all containers are running
<compose> ps
```

### Test the Public Route
```bash
curl -i http://localhost/health
curl -i http://localhost/nginx-health
```

### Test the Full Pipeline
```bash
curl -X POST http://localhost/telemetry \
  -H "Content-Type: application/json" \
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

### Prove B and C Are Internal Only
```bash
# These should fail (connection refused or timeout)
curl -i --connect-timeout 3 http://localhost:3002/health
curl -i --connect-timeout 3 http://localhost:3003/health
```

### View Logs
```bash
# All services
<compose> logs

# Specific service
<compose> logs ground-station-api
<compose> logs telemetry-parser
<compose> logs anomaly-detector
<compose> logs nginx
```

### Stop and Restart a Service
```bash
# Stop Telemetry Parser
<compose> stop telemetry-parser

# Start it again
<compose> start telemetry-parser

# Restart Ground Station API
<compose> restart ground-station-api
```

### Shut Everything Down
```bash
<compose> down
```

### Trace a Request
```bash
# Send a request with a known ID
curl -X POST http://localhost/telemetry \
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

# Trace it through logs
<compose> logs | grep demo-container-001
```

### Failure and Recovery Test
```bash
# Stop Telemetry Parser
<compose> stop telemetry-parser

# Send request (should fail gracefully)
curl -X POST http://localhost/telemetry \
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

# Check logs
<compose> logs ground-station-api

# Recover
<compose> start telemetry-parser

# Verify recovery
curl -i http://localhost/health
```

---

## API Reference

### Service A: Ground Station API (Port 3001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/telemetry` | POST | Receive telemetry frame from satellite |
| `/callback` | POST | Receive callback from Service C |

### Service B: Telemetry Parser (Port 3002)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/parse` | POST | Parse telemetry frame, forward to Service C |

### Service C: Anomaly Detector (Port 3003)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/analyze` | POST | Analyze telemetry, callback to Service A |

---

## Testing

### Automated End-to-End Test

```bash
sudo bash scripts/test-end-to-end.sh
```

### Generate Mock Telemetry

```bash
# Nominal (healthy satellite)
sudo bash scripts/generate-telemetry.sh nominal

# Anomaly (problems detected)
sudo bash scripts/generate-telemetry.sh anomaly
```

### Trace a Request

```bash
# Replace with actual request ID from logs
sudo bash scripts/trace-request.sh req-abc123
```

### Manual Tests

```bash
# Health checks
curl http://localhost/health
curl http://localhost:3002/health
curl http://localhost:3003/health

# Send telemetry with anomalies
curl -X POST http://localhost/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "satellite_id": "SAT-001",
    "mission_id": "MISSION-ALPHA-7",
    "timestamp": "2026-06-18T09:30:00Z",
    "telemetry_frame": {
      "battery_voltage": 10.5,
      "solar_panel_temp": 95.0,
      "gyro_x": 5.5,
      "gyro_y": -3.2,
      "gyro_z": 0.10,
      "signal_strength_dbm": -140,
      "downlink_frequency": 437.5
    }
  }'
```

---

## 📦 Proof Pack for Reviewers

This section provides command output that proves the system works as designed. Run these commands and compare with the expected output.

### 1. Service Health Proof

```bash
sudo systemctl status telemetry-parser anomaly-detector ground-station-api --no-pager
```

**Expected:** All three services show `Active: active (running)`

### 2. Readiness Gate Proof

```bash
sudo journalctl -u ground-station-api -n 5 --no-pager
```

**Expected:** Lines showing "Waiting for dependencies to be ready..." followed by "Dependencies ready, starting Service A"

### 3. End-to-End Flow Proof

```bash
curl -X POST http://localhost/telemetry \
  -H "Content-Type: application/json" \
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

**Expected:** `{"status":"accepted","ground_station_id":"GS-Nairobi-1","processing_request_id":"req-...","satellite_id":"SAT-001","message":"Telemetry frame queued for processing"}`

### 4. Request Tracing Proof

```bash
# Replace req-XXXXXX with actual request ID from step 3
sudo bash scripts/trace-request.sh req-XXXXXX
```

**Expected:** Colored output showing the request through all 3 services with the same `processing_request_id`

### 5. Network Security Proof

```bash
# From the VM itself (should work)
curl http://localhost:3002/health

# From another machine (should fail - timeout or connection refused)
curl --connect-timeout 3 http://<VM_IP>:3002/health
```

### 6. Reboot Recovery Proof

```bash
# Reboot the VM
sudo reboot

# After SSH back in, verify services auto-started
sudo systemctl status telemetry-parser anomaly-detector ground-station-api
curl http://localhost/health
```

**Expected:** All services running, health endpoint responds

### 7. Failure Recovery Proof

```bash
# Stop Service B
sudo systemctl stop telemetry-parser

# Check Service A handles it gracefully
curl -X POST http://localhost/telemetry \
  -H "Content-Type: application/json" \
  -d '{"satellite_id":"SAT-001","mission_id":"MISSION-ALPHA-7","timestamp":"2026-06-18T09:30:00Z","telemetry_frame":{"battery_voltage":14.2,"solar_panel_temp":45.3,"gyro_x":0.01,"gyro_y":-0.02,"gyro_z":0.00,"signal_strength_dbm":-85,"downlink_frequency":437.5}}'

# Expected: HTTP 502 with "Telemetry parser unreachable"

# Restart Service B
sudo systemctl start telemetry-parser
sleep 3
sudo systemctl start ground-station-api

# Verify recovery
curl http://localhost:3002/health
curl http://localhost/health
```

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `status 226/NAMESPACE` | systemd security settings too strict | Already fixed — remove `ProtectSystem=strict` and `ProtectHome=true` from `.service` files |
| `status 203/EXEC` | Virtual environment doesn't exist | Run `install.sh` or create venv manually |
| `status 200/CHDIR` | Working directory missing | Check paths in `.service` files match your deployment location |
| Service A won't start | Service B or C not ready | Start B and C first: `sudo systemctl start telemetry-parser anomaly-detector` |
| Can't reach port 3002 from outside | Firewall blocking | Correct — internal services should NOT be accessible externally |
| `Connection refused` on port 80 | Nginx not running | `sudo systemctl restart nginx` |
| `NameResolutionError` for `telemetry-parser` | `/etc/hosts` missing service hostnames | Add `127.0.0.1 telemetry-parser` to `/etc/hosts` |
| Logs show `processing_request_id` not found | Request ID mismatch | Check that all services use the same ID field name |

### Check Service Status

```bash
sudo systemctl status telemetry-parser anomaly-detector ground-station-api
```

### Check Logs

```bash
sudo journalctl -u telemetry-parser -n 50
sudo journalctl -u anomaly-detector -n 50
sudo journalctl -u ground-station-api -n 50
```

### Check Firewall

```bash
sudo ufw status verbose
sudo iptables -L INPUT -n --line-numbers | grep 300
```

### Reset Everything

```bash
# Stop all services
sudo systemctl stop ground-station-api telemetry-parser anomaly-detector

# Reset failed state
sudo systemctl reset-failed

# Restart
sudo systemctl start telemetry-parser anomaly-detector
sleep 3
sudo systemctl start ground-station-api
```

---

## Project Structure

```
devops-satellite-telemetry/
├── README.md                          # This file
├── install.sh                         # One-command VM deployment script
├── docker-compose.yml                 # Docker Compose orchestration
├── .dockerignore                      # Files to exclude from Docker build context
│
├── service-a/                         # Ground Station API (Port 3001)
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile                     # Container image for Service A
│
├── service-b/                         # Telemetry Parser (Port 3002)
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile                     # Container image for Service B
│
├── service-c/                         # Anomaly Detector (Port 3003)
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile                     # Container image for Service C
│
├── nginx/
│   ├── satellite-telemetry            # Nginx site config (VM deployment)
│   └── nginx-docker.conf             # Nginx config (Docker deployment)
│
├── systemd/                           # systemd service definitions
│   ├── ground-station-api.service
│   ├── telemetry-parser.service
│   └── anomaly-detector.service
│
├── scripts/                           # Testing and utility scripts
│   ├── test-end-to-end.sh
│   ├── trace-request.sh
│   ├── generate-telemetry.sh
│   └── configure-firewall.sh
│
└── docs/                              # Documentation and validation
    └── CONTAINER_VALIDATION.md        # Docker Compose validation evidence
```

---

## Team

| Member | Role | Files |
|--------|------|-------|
| **Yordanos** | Project Lead, Service A, Integration | `service-a/`, `nginx/`, `systemd/`, `install.sh`, `README.md` |
| **Saloi** | Service B — Telemetry Parser | `service-b/` |
| **Berissa** | Service C — Anomaly Detector, Scripts | `service-c/`, `scripts/` |
| **Arsema** | Docker Compose & Documentation | `docker-compose.yml`, `.dockerignore`, `nginx/nginx-docker.conf`, `docs/CONTAINER_VALIDATION.md`, `README.md` (Docker section) |

---

---

## License

This project was created for educational purposes as part of a DevOps/Systems Engineering course.

---

## Notes for Trainers/Reviewers

- All services produce structured JSON logs with `processing_request_id` for request tracing
- The same `processing_request_id` propagates through Service A → B → C → A callback
- Internal services (B, C) are blocked from external access by firewall (VM) or Docker network isolation (containers)
- Services restart automatically on crash via systemd (`Restart=always`) or Docker Compose (`restart: unless-stopped`)
- Nginx is the only public entry point (port 80) in both VM and Docker deployments
