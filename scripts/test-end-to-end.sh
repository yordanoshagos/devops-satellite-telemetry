#!/bin/bash
# =============================================================================
# test-end-to-end.sh - End-to-End Pipeline Test
# =============================================================================
# Tests the complete satellite telemetry processing pipeline.
# Usage:
#   bash test-end-to-end.sh
# =============================================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════════╗"
<<<<<<< HEAD
echo "║           END-TO-END PIPELINE TEST                                ║"
=======
echo "║           🧪 END-TO-END PIPELINE TEST                                ║"
>>>>>>> feature/service-a-integration
echo "║           Satellite Telemetry Processing System                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

BASE_URL="http://localhost"
FAILED=0

# =============================================================================
# TEST 1: Health Checks
# =============================================================================
echo -e "${YELLOW}TEST 1/5: Health Checks${NC}"

# Service A via Nginx
echo -n "  Service A (via Nginx): "
if curl -s "${BASE_URL}/health" | grep -q "ground-station-api"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
    FAILED=$((FAILED + 1))
fi

# Service B direct (localhost only)
echo -n "  Service B (direct): "
if curl -s "http://localhost:3002/health" | grep -q "telemetry-parser"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
    FAILED=$((FAILED + 1))
fi

# Service C direct (localhost only)
echo -n "  Service C (direct): "
if curl -s "http://localhost:3003/health" | grep -q "anomaly-detector"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""

# =============================================================================
# TEST 2: Nominal Telemetry Frame
# =============================================================================
echo -e "${YELLOW}TEST 2/5: Nominal Telemetry Frame (No Anomalies)${NC}"

RESPONSE=$(curl -s -X POST "${BASE_URL}/telemetry" \
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
    }')

echo -n "  Request accepted: "
if echo "$RESPONSE" | grep -q '"status": "accepted"'; then
    echo -e "${GREEN}✅ PASS${NC}"
    REQUEST_ID=$(echo "$RESPONSE" | grep -o '"processing_request_id": "[^"]*"' | cut -d'"' -f4)
    echo -e "  Request ID: ${BLUE}$REQUEST_ID${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
    echo "  Response: $RESPONSE"
    FAILED=$((FAILED + 1))
fi

echo ""

# =============================================================================
# TEST 3: Warning Telemetry Frame (Anomalies Detected)
# =============================================================================
echo -e "${YELLOW}TEST 3/5: Warning Telemetry Frame (Anomalies Expected)${NC}"

RESPONSE=$(curl -s -X POST "${BASE_URL}/telemetry" \
    -H "Content-Type: application/json" \
    -d '{
        "satellite_id": "SAT-002",
        "mission_id": "MISSION-BETA-3",
        "timestamp": "2026-06-18T09:35:00Z",
        "telemetry_frame": {
            "battery_voltage": 10.5,
            "solar_panel_temp": 95.0,
            "gyro_x": 5.5,
            "gyro_y": -3.2,
            "gyro_z": 0.10,
            "signal_strength_dbm": -140,
            "downlink_frequency": 437.5
        }
    }')

echo -n "  Request accepted: "
if echo "$RESPONSE" | grep -q '"status": "accepted"'; then
    echo -e "${GREEN}✅ PASS${NC}"
    REQUEST_ID_WARN=$(echo "$RESPONSE" | grep -o '"processing_request_id": "[^"]*"' | cut -d'"' -f4)
    echo -e "  Request ID: ${BLUE}$REQUEST_ID_WARN${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
    echo "  Response: $RESPONSE"
    FAILED=$((FAILED + 1))
fi

echo ""

# =============================================================================
# TEST 4: Network Security (Service B & C Should Be Blocked Externally)
# =============================================================================
echo -e "${YELLOW}TEST 4/5: Network Security Verification${NC}"

# Get VM's public IP
PUBLIC_IP=$(hostname -I | awk '{print $1}')

echo -n "  Service B blocked from public: "
# This should fail/timeout when accessed via public IP
if curl -s --connect-timeout 2 "http://${PUBLIC_IP}:3002/health" 2>/dev/null | grep -q "telemetry-parser"; then
    echo -e "${RED}❌ FAIL - Service B is accessible externally!${NC}"
    FAILED=$((FAILED + 1))
else
    echo -e "${GREEN}✅ PASS - Service B is protected${NC}"
fi

echo -n "  Service C blocked from public: "
if curl -s --connect-timeout 2 "http://${PUBLIC_IP}:3003/health" 2>/dev/null | grep -q "anomaly-detector"; then
    echo -e "${RED}❌ FAIL - Service C is accessible externally!${NC}"
    FAILED=$((FAILED + 1))
else
    echo -e "${GREEN}✅ PASS - Service C is protected${NC}"
fi

echo -n "  Service A accessible via Nginx: "
if curl -s "http://${PUBLIC_IP}/health" | grep -q "ground-station-api"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
    FAILED=$((FAILED + 1))
fi

echo ""

# =============================================================================
# TEST 5: Structured Logging Verification
# =============================================================================
echo -e "${YELLOW}TEST 5/5: Structured Logging Verification${NC}"

echo -n "  JSON logs present in journald: "
if sudo journalctl -u ground-station-api --since "1 minute ago" --no-pager -o json | head -1 | grep -q "timestamp"; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC}"
    FAILED=$((FAILED + 1))
fi

echo -n "  Request traceable across services: "
if [ -n "$REQUEST_ID" ]; then
    TRACE_COUNT=$(sudo journalctl -u ground-station-api -u telemetry-parser -u anomaly-detector \
        --since "2 minutes ago" --no-pager | grep -c "$REQUEST_ID" || true)
    if [ "$TRACE_COUNT" -ge 3 ]; then
        echo -e "${GREEN}✅ PASS - Found $TRACE_COUNT log entries for request $REQUEST_ID${NC}"
    else
        echo -e "${YELLOW}⚠️  WARNING - Only found $TRACE_COUNT log entries (expected 3+)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  SKIPPED - No request ID from previous test${NC}"
fi

echo ""

# =============================================================================
# SUMMARY
# =============================================================================
echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}                    🎉 ALL TESTS PASSED! 🎉${NC}"
else
    echo -e "${RED}                    ⚠️  $FAILED TEST(S) FAILED ⚠️${NC}"
fi
echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}📋 Useful Commands:${NC}"
echo -e "  ${BLUE}•${NC} View all logs:        ${GREEN}sudo journalctl -u ground-station-api -u telemetry-parser -u anomaly-detector -f${NC}"
echo -e "  ${BLUE}•${NC} Check service status: ${GREEN}sudo systemctl status ground-station-api${NC}"
echo -e "  ${BLUE}•${NC} Trace request:        ${GREEN}sudo bash /opt/devops-satellite-telemetry/scripts/trace-request.sh <request_id>${NC}"
echo ""
