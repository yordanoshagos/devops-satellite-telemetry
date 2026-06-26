#!/bin/bash
# =============================================================================
# install.sh - Satellite Telemetry Pipeline Deployment Script
# =============================================================================
# One-command deployment for the Ground Station Telemetry Processing System.
# Run this as root or with sudo on your Ubuntu VM.
#
# Usage:
#   sudo bash install.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_NAME="devops-satellite-telemetry"
INSTALL_DIR="/opt/${PROJECT_NAME}"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║        🛰️  SATELLITE TELEMETRY PIPELINE DEPLOYMENT                  ║"
echo "║        Ground Station Telemetry Processing System                    ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =============================================================================
# STEP 1: Check if running as root
# =============================================================================
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root or with sudo: sudo bash install.sh${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Step 1/10: Checking prerequisites...${NC}"

# =============================================================================
# STEP 2: Update system and install dependencies
# =============================================================================
echo -e "${YELLOW}📦 Step 2/10: Installing system dependencies...${NC}"
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx curl ufw

echo -e "${GREEN}✅ System dependencies installed${NC}"

# =============================================================================
# STEP 3: Create service users (no login, for security)
# =============================================================================
echo -e "${YELLOW}👤 Step 3/10: Creating service users...${NC}"

# Create users if they don't exist
for user in groundstation telemetry anomaly; do
    if ! id "$user" &>/dev/null; then
        useradd -r -s /usr/sbin/nologin -M "$user"
        echo -e "  ${GREEN}✓${NC} Created user: $user"
    else
        echo -e "  ${BLUE}ℹ${NC} User already exists: $user"
    fi
done

# =============================================================================
# STEP 4: Set up project directory
# =============================================================================
echo -e "${YELLOW}📁 Step 4/10: Setting up project directory...${NC}"

# Determine source directory (where install.sh is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# If running from /opt, use current dir. Otherwise copy to /opt
if [[ "$SCRIPT_DIR" == "$INSTALL_DIR"* ]]; then
    echo -e "  ${BLUE}ℹ${NC} Already in $INSTALL_DIR"
else
    echo -e "  ${BLUE}ℹ${NC} Copying project to $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
fi

# Set ownership
chown -R root:root "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"

echo -e "${GREEN}✅ Project deployed to $INSTALL_DIR${NC}"

# =============================================================================
# STEP 5: Install Python dependencies for each service
# =============================================================================
echo -e "${YELLOW}🐍 Step 5/10: Installing Python dependencies...${NC}"

for service in service-a service-b service-c; do
    echo -e "  ${BLUE}ℹ${NC} Setting up $service..."
    cd "$INSTALL_DIR/$service"

    # Create virtual environment
    python3 -m venv venv

    # Activate and install requirements
    source venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    deactivate

    echo -e "  ${GREEN}✓${NC} $service dependencies installed"
done

echo -e "${GREEN}✅ All Python dependencies installed${NC}"

# =============================================================================
# STEP 6: Configure /etc/hosts for service discovery
# =============================================================================
echo -e "${YELLOW}🌐 Step 6/10: Configuring service discovery...${NC}"

# Add service names to /etc/hosts for local resolution
if ! grep -q "telemetry-parser" /etc/hosts; then
    echo "127.0.0.1 telemetry-parser" >> /etc/hosts
    echo -e "  ${GREEN}✓${NC} Added telemetry-parser to /etc/hosts"
fi

if ! grep -q "anomaly-detector" /etc/hosts; then
    echo "127.0.0.1 anomaly-detector" >> /etc/hosts
    echo -e "  ${GREEN}✓${NC} Added anomaly-detector to /etc/hosts"
fi

if ! grep -q "ground-station-api" /etc/hosts; then
    echo "127.0.0.1 ground-station-api" >> /etc/hosts
    echo -e "  ${GREEN}✓${NC} Added ground-station-api to /etc/hosts"
fi

# Also add to cloud-init template if it exists (for reboot persistence)
if [ -d "/etc/cloud/templates" ]; then
    CLOUD_HOSTS="/etc/cloud/templates/hosts.debian.tmpl"
    if [ -f "$CLOUD_HOSTS" ]; then
        if ! grep -q "telemetry-parser" "$CLOUD_HOSTS"; then
            echo "127.0.0.1 telemetry-parser" >> "$CLOUD_HOSTS"
            echo -e "  ${GREEN}✓${NC} Added telemetry-parser to cloud-init template"
        fi
        if ! grep -q "anomaly-detector" "$CLOUD_HOSTS"; then
            echo "127.0.0.1 anomaly-detector" >> "$CLOUD_HOSTS"
            echo -e "  ${GREEN}✓${NC} Added anomaly-detector to cloud-init template"
        fi
        if ! grep -q "ground-station-api" "$CLOUD_HOSTS"; then
            echo "127.0.0.1 ground-station-api" >> "$CLOUD_HOSTS"
            echo -e "  ${GREEN}✓${NC} Added ground-station-api to cloud-init template"
        fi
    else
        echo -e "  ${BLUE}ℹ${NC} cloud-init template not found, skipping (VM may not use cloud-init)"
    fi
else
    echo -e "  ${BLUE}ℹ${NC} cloud-init not installed, /etc/hosts entries will persist on reboot"
fi

echo -e "${GREEN}✅ Service discovery configured${NC}"

# =============================================================================
# STEP 7: Install systemd service files
# =============================================================================
echo -e "${YELLOW}⚙️  Step 7/10: Installing systemd services...${NC}"

cp "$INSTALL_DIR/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload

echo -e "${GREEN}✅ systemd services installed and daemon reloaded${NC}"

# =============================================================================
# STEP 8: Configure Nginx reverse proxy
# =============================================================================
echo -e "${YELLOW}🌐 Step 8/10: Configuring Nginx reverse proxy...${NC}"

# Remove default site if exists
rm -f /etc/nginx/sites-enabled/default

# Copy our configuration
cp "$INSTALL_DIR/nginx/satellite-telemetry.conf" /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/satellite-telemetry.conf /etc/nginx/sites-enabled/

# Test Nginx configuration
nginx -t

# Restart Nginx
systemctl restart nginx
systemctl enable nginx

echo -e "${GREEN}✅ Nginx configured and running${NC}"

# =============================================================================
# STEP 9: Configure firewall
# =============================================================================
echo -e "${YELLOW}🛡️  Step 9/10: Configuring firewall...${NC}"

# Reset UFW to defaults
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (port 22)
ufw allow 22/tcp

# Allow Nginx (port 80) - public entry point
ufw allow 80/tcp

# Allow internal services on localhost only
# (These are handled by iptables rules below for loopback-only)

# Enable UFW
echo "y" | ufw enable

# Additional iptables rules to ensure internal services are localhost-only
iptables -F INPUT
iptables -P INPUT DROP
iptables -A INPUT -i lo -j ACCEPT
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT

# Save iptables rules
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

echo -e "${GREEN}✅ Firewall configured${NC}"
echo -e "  ${BLUE}ℹ${NC} Port 80 (Nginx) - OPEN to public"
echo -e "  ${BLUE}ℹ${NC} Port 22 (SSH) - OPEN to public"
echo -e "  ${BLUE}ℹ${NC} Ports 3001-3003 - LOCALHOST ONLY"

# =============================================================================
# STEP 10: Start services in dependency order
# =============================================================================
echo -e "${YELLOW}🚀 Step 10/10: Starting services...${NC}"

# Start internal services first
echo -e "  ${BLUE}ℹ${NC} Starting telemetry-parser (Service B)..."
systemctl start telemetry-parser
systemctl enable telemetry-parser

echo -e "  ${BLUE}ℹ${NC} Starting anomaly-detector (Service C)..."
systemctl start anomaly-detector
systemctl enable anomaly-detector

# Wait a moment for internal services to be ready
sleep 3

# Start public-facing service last (it depends on B and C)
echo -e "  ${BLUE}ℹ${NC} Starting ground-station-api (Service A)..."
systemctl start ground-station-api
systemctl enable ground-station-api

# Wait for Service A to be ready
sleep 2

echo -e "${GREEN}✅ All services started${NC}"

# =============================================================================
# VERIFICATION
# =============================================================================
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    🎉 DEPLOYMENT COMPLETE! 🎉${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}📊 Service Status:${NC}"
echo ""
systemctl status telemetry-parser --no-pager -l | head -5
systemctl status anomaly-detector --no-pager -l | head -5
systemctl status ground-station-api --no-pager -l | head -5

echo ""
echo -e "${YELLOW}🔍 Verification Commands:${NC}"
echo -e "  ${BLUE}•${NC} Check all services:     ${GREEN}sudo systemctl status ground-station-api telemetry-parser anomaly-detector${NC}"
echo -e "  ${BLUE}•${NC} Test health endpoint:   ${GREEN}curl http://localhost/health${NC}"
echo -e "  ${BLUE}•${NC} View logs:            ${GREEN}sudo journalctl -u ground-station-api -f${NC}"
echo -e "  ${BLUE}•${NC} Trace a request:      ${GREEN}sudo bash $INSTALL_DIR/scripts/trace-request.sh req-XXXXXX${NC}"
echo -e "  ${BLUE}•${NC} Run end-to-end test:  ${GREEN}sudo bash $INSTALL_DIR/scripts/test-end-to-end.sh${NC}"
echo ""
echo -e "${YELLOW}📁 Installation Directory:${NC} ${GREEN}$INSTALL_DIR${NC}"
echo -e "${YELLOW}🌐 Public Access:${NC}        ${GREEN}http://$(hostname -I | awk '{print $1}')/${NC}"
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════════════════${NC}"
