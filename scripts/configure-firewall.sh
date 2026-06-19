#!/bin/bash
# Firewall configuration for Satellite Telemetry Pipeline
# This script configures iptables to:
# 1. Allow SSH (port 22) for remote management
# 2. Allow Nginx (port 80) as the only public entry point
# 3. Allow internal services (3001-3003) only on localhost/loopback
# 4. Block direct external access to internal services (3002, 3003)

set -e

echo "=== Configuring Firewall for Satellite Telemetry Pipeline ==="

# Flush existing rules
sudo iptables -F
sudo iptables -X

# Set default policies
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# Allow loopback traffic (critical for internal service communication)
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A OUTPUT -o lo -j ACCEPT

# Allow established and related connections
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Allow SSH (port 22) - adjust if using different port
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow Nginx (port 80) - public entry point
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT

# Allow Service A (port 3001) on localhost only (for Nginx proxy)
sudo iptables -A INPUT -i lo -p tcp --dport 3001 -j ACCEPT

# Block direct external access to Service B (port 3002) and Service C (port 3003)
# These are internal-only and should not be accessible from outside
# No rules needed - default DROP policy handles this

echo "=== Firewall Rules Applied ==="
echo ""
echo "Allowed from ANYWHERE:"
echo "  - Port 22 (SSH)"
echo "  - Port 80 (Nginx - Public Gateway)"
echo ""
echo "Allowed from LOCALHOST ONLY:"
echo "  - Port 3001 (Ground Station API - via Nginx proxy)"
echo "  - Port 3002 (Telemetry Parser - internal only)"
echo "  - Port 3003 (Anomaly Detector - internal only)"
echo ""
echo "Blocked from EXTERNAL:"
echo "  - Port 3002 (Telemetry Parser)"
echo "  - Port 3003 (Anomaly Detector)"
echo ""

# Display current rules
echo "=== Current iptables Rules ==="
sudo iptables -L -n --line-numbers

echo ""
echo "=== Firewall configuration complete ==="
echo "To save rules permanently, run: sudo iptables-save > /etc/iptables/rules.v4"
