#!/bin/bash
# =============================================================================
# trace-request.sh - Request Tracing Utility
# =============================================================================
# Traces a single request across all services using the processing_request_id.
#
# Usage:
#   bash trace-request.sh <processing_request_id>
#   bash trace-request.sh req-abc123
# =============================================================================

if [ -z "$1" ]; then
    echo "Usage: bash trace-request.sh <processing_request_id>"
    echo "Example: bash trace-request.sh req-abc123"
    exit 1
fi

REQUEST_ID="$1"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║            REQUEST TRACE: $REQUEST_ID"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}Tracing request across all services...${NC}"
echo ""

# Search all service logs for this request ID
sudo journalctl -u ground-station-api -u telemetry-parser -u anomaly-detector \
    --since "30 minutes ago" --no-pager | grep "$REQUEST_ID" | while read line; do

    # Color-code by service
    if echo "$line" | grep -q "ground-station-api"; then
        echo -e "${GREEN}[Ground Station]${NC} $line"
    elif echo "$line" | grep -q "telemetry-parser"; then
        echo -e "${YELLOW}[Telemetry Parser]${NC} $line"
    elif echo "$line" | grep -q "anomaly-detector"; then
        echo -e "${BLUE}[Anomaly Detector]${NC} $line"
    else
        echo "$line"
    fi
done

echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
