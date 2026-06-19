#!/bin/bash
# =============================================================================
# generate-telemetry.sh - Mock Satellite Telemetry Generator
# =============================================================================
# Generates realistic satellite telemetry frames for testing.
#
# Usage:
#   bash generate-telemetry.sh [nominal|warning|critical]
# =============================================================================

MODE="${1:-nominal}"
BASE_URL="http://localhost"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════════╗"
<<<<<<< HEAD
echo "║           MOCK SATELLITE TELEMETRY GENERATOR                    ║"
=======
echo "║           📡 MOCK SATELLITE TELEMETRY GENERATOR                    ║"
>>>>>>> feature/service-a-integration
echo "║           Mode: $MODE"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Generate random satellite and mission IDs
SAT_ID="SAT-$(printf '%03d' $((RANDOM % 999 + 1)))"
MISSION_ID="MISSION-$(tr -dc 'A-Z' < /dev/urandom | head -c 5)-$((RANDOM % 99 + 1))"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ "$MODE" == "nominal" ]; then
    # All values within safe thresholds
    BATTERY=$(awk -v min=12.5 -v max=15.5 'BEGIN{srand(); print min+rand()*(max-min)}')
    TEMP=$(awk -v min=-20 -v max=60 'BEGIN{srand(); print min+rand()*(max-min)}')
    GYRO_X=$(awk -v min=-0.5 -v max=0.5 'BEGIN{srand(); print min+rand()*(max-min)}')
    GYRO_Y=$(awk -v min=-0.5 -v max=0.5 'BEGIN{srand(); print min+rand()*(max-min)}')
    GYRO_Z=$(awk -v min=-0.5 -v max=0.5 'BEGIN{srand(); print min+rand()*(max-min)}')
    SIGNAL=$((RANDOM % 40 - 110))  # -110 to -70 dBm

elif [ "$MODE" == "warning" ]; then
    # Some values outside safe thresholds
    BATTERY=$(awk -v min=10.0 -v max=11.5 'BEGIN{srand(); print min+rand()*(max-min)}')
    TEMP=$(awk -v min=75 -v max=95 'BEGIN{srand(); print min+rand()*(max-min)}')
    GYRO_X=$(awk -v min=2.0 -v max=5.0 'BEGIN{srand(); print min+rand()*(max-min)}')
    GYRO_Y=$(awk -v min=-5.0 -v max=-2.0 'BEGIN{srand(); print min+rand()*(max-min)}')
    GYRO_Z=$(awk -v min=-0.5 -v max=0.5 'BEGIN{srand(); print min+rand()*(max-min)}')
    SIGNAL=$((RANDOM % 30 - 145))  # -145 to -115 dBm

elif [ "$MODE" == "critical" ]; then
    # Severely out-of-range values
    BATTERY=$(awk -v min=8.0 -v max=10.0 'BEGIN{srand(); print min+rand()*(max-min)}')
    TEMP=$(awk -v min=90 -v max=110 'BEGIN{srand(); print min+rand()*(max-min)}')
    GYRO_X=$(awk -v min=5.0 -v max=10.0 'BEGIN{srand(); print min+rand()*(max-min)}')
    GYRO_Y=$(awk -v min=-10.0 -v max=-5.0 'BEGIN{srand(); print min+rand()*(max-min)}')
    GYRO_Z=$(awk -v min=-2.0 -v max=2.0 'BEGIN{srand(); print min+rand()*(max-min)}')
    SIGNAL=$((RANDOM % 20 - 155))  # -155 to -135 dBm

else
    echo "Usage: bash generate-telemetry.sh [nominal|warning|critical]"
    exit 1
fi

# Build JSON payload
PAYLOAD=$(cat <<EOF
{
    "satellite_id": "$SAT_ID",
    "mission_id": "$MISSION_ID",
    "timestamp": "$TIMESTAMP",
    "telemetry_frame": {
        "battery_voltage": $(printf "%.2f" $BATTERY),
        "solar_panel_temp": $(printf "%.2f" $TEMP),
        "gyro_x": $(printf "%.2f" $GYRO_X),
        "gyro_y": $(printf "%.2f" $GYRO_Y),
        "gyro_z": $(printf "%.2f" $GYRO_Z),
        "signal_strength_dbm": $SIGNAL,
        "downlink_frequency": 437.5
    }
}
EOF
)

echo -e "${YELLOW}Generated Telemetry Frame:${NC}"
echo "$PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "$PAYLOAD"
echo ""

echo -e "${YELLOW}Sending to Ground Station API...${NC}"
RESPONSE=$(curl -s -X POST "${BASE_URL}/telemetry" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

echo -e "${GREEN}Response:${NC}"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

# Extract and display request ID
REQUEST_ID=$(echo "$RESPONSE" | grep -o '"processing_request_id": "[^"]*"' | cut -d'"' -f4)
if [ -n "$REQUEST_ID" ]; then
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Request ID: ${GREEN}$REQUEST_ID${NC}"
    echo -e "${YELLOW}Trace this request: ${GREEN}sudo bash /opt/devops-satellite-telemetry/scripts/trace-request.sh $REQUEST_ID${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
fi
