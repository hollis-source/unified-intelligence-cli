#!/bin/bash
# Server Security Setup Script
# Configures fail2ban and ufw for unified-intelligence-cli server

set -e

echo "=================================================="
echo "Server Security Setup"
echo "=================================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (sudo)"
    exit 1
fi

echo "[1/6] Installing fail2ban..."
apt-get update
apt-get install -y fail2ban

echo "[2/6] Configuring fail2ban..."
# Create local configuration
cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
# Ban hosts for 1 hour
bantime = 3600

# Find time window (10 minutes)
findtime = 600

# Max retries before ban
maxretry = 5

# Destination email for notifications
destemail = admin@localhost

# Sender email
sender = fail2ban@localhost

# Action on ban (ban + send email)
action = %(action_mwl)s

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-noscript]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 6

[nginx-badbots]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 2

[nginx-noproxy]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 2

# Custom: Project Builder API abuse
[unified-intelligence-api]
enabled = true
port = http,https
filter = unified-intelligence-api
logpath = /var/log/unified-intelligence/app.log
maxretry = 10
findtime = 300
bantime = 1800
EOF

# Create custom filter for API abuse
mkdir -p /etc/fail2ban/filter.d
cat > /etc/fail2ban/filter.d/unified-intelligence-api.conf <<'EOF'
# Fail2Ban filter for unified-intelligence-cli API abuse

[Definition]
# Match authentication failures
failregex = ^.* - .*Authentication failed.*from <HOST>
            ^.* - .*Invalid API key.*from <HOST>
            ^.* - .*Rate limit exceeded.*for <HOST>
            ^.* - .*Forbidden.*from <HOST>

ignoreregex =
EOF

# Enable and start fail2ban
systemctl enable fail2ban
systemctl restart fail2ban

echo "[3/6] Configuring UFW firewall..."

# Reset UFW to defaults
ufw --force reset

# Set default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (CRITICAL - don't lock yourself out!)
ufw allow 22/tcp comment 'SSH'

# Allow HTTP/HTTPS for API
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Allow Redis (localhost only)
ufw allow from 127.0.0.1 to any port 6379 comment 'Redis localhost'

# Allow PostgreSQL (localhost only) - if using instead of SQLite
ufw allow from 127.0.0.1 to any port 5432 comment 'PostgreSQL localhost'

# Rate limiting for SSH (prevent brute force)
ufw limit 22/tcp comment 'SSH rate limit'

echo "[4/6] Enabling UFW..."
# Enable firewall
ufw --force enable

echo "[5/6] Configuring additional security..."

# Enable SYN cookies (DDoS protection)
sysctl -w net.ipv4.tcp_syncookies=1

# Disable IP forwarding (unless needed for Docker)
# sysctl -w net.ipv4.ip_forward=0

# Ignore ICMP redirects
sysctl -w net.ipv4.conf.all.accept_redirects=0
sysctl -w net.ipv6.conf.all.accept_redirects=0

# Ignore source routed packets
sysctl -w net.ipv4.conf.all.accept_source_route=0

# Make these permanent
cat >> /etc/sysctl.conf <<'EOF'

# Added by unified-intelligence-cli security setup
net.ipv4.tcp_syncookies=1
net.ipv4.conf.all.accept_redirects=0
net.ipv6.conf.all.accept_redirects=0
net.ipv4.conf.all.accept_source_route=0
EOF

echo "[6/6] Status check..."
echo ""
echo "Fail2ban status:"
systemctl status fail2ban --no-pager | head -5
echo ""
echo "UFW status:"
ufw status verbose
echo ""
echo "Fail2ban jails:"
fail2ban-client status
echo ""

echo "=================================================="
echo "✅ Server security setup complete!"
echo "=================================================="
echo ""
echo "Summary:"
echo "  - fail2ban: Installed and configured"
echo "  - UFW: Enabled with SSH, HTTP, HTTPS allowed"
echo "  - SYN cookies: Enabled (DDoS protection)"
echo "  - IP redirects: Disabled"
echo ""
echo "Important:"
echo "  - SSH is protected with rate limiting"
echo "  - 3 failed SSH attempts = 2 hour ban"
echo "  - 10 API failures in 5 min = 30 min ban"
echo "  - Check logs: journalctl -u fail2ban -f"
echo ""
