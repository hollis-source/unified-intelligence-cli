# Server Security Setup - Installation Instructions

**Date**: October 6, 2025
**Purpose**: Configure fail2ban and ufw on local server for production security

---

## Quick Start

```bash
# Run the automated setup script (requires sudo)
sudo ./scripts/setup_server_security.sh
```

This script will:
1. Install fail2ban
2. Configure fail2ban with custom rules for unified-intelligence-cli
3. Configure UFW firewall
4. Enable security hardening (SYN cookies, disable redirects)
5. Display status

**Estimated time**: 2-3 minutes

---

## What Gets Configured

### Fail2ban Protection

**SSH Protection**:
- Max 3 failed attempts
- Ban time: 2 hours (7200 seconds)
- Protects port 22

**Nginx Protection** (if using nginx):
- HTTP auth failures
- Bad bot blocking
- Script injection attempts
- Proxy abuse

**API Protection** (unified-intelligence-cli):
- Authentication failures
- Invalid API keys
- Rate limit violations
- Ban after 10 failures in 5 minutes
- Ban time: 30 minutes

### UFW Firewall Rules

**Allowed Incoming**:
- Port 22 (SSH) - with rate limiting
- Port 80 (HTTP)
- Port 443 (HTTPS)

**Allowed Localhost Only**:
- Port 6379 (Redis)
- Port 5432 (PostgreSQL)

**Default Policy**:
- Incoming: DENY
- Outgoing: ALLOW

### System Hardening

**SYN Cookies**: Enabled (DDoS protection)
**IP Forwarding**: Disabled (unless Docker needs it)
**ICMP Redirects**: Disabled
**Source Routing**: Disabled

---

## Manual Installation (Alternative)

If you prefer to run commands manually:

### Step 1: Install Packages

```bash
sudo apt-get update
sudo apt-get install -y fail2ban ufw
```

### Step 2: Configure Fail2ban

Create `/etc/fail2ban/jail.local`:

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200

[unified-intelligence-api]
enabled = true
port = http,https
filter = unified-intelligence-api
logpath = /var/log/unified-intelligence/app.log
maxretry = 10
findtime = 300
bantime = 1800
```

Create `/etc/fail2ban/filter.d/unified-intelligence-api.conf`:

```ini
[Definition]
failregex = ^.* - .*Authentication failed.*from <HOST>
            ^.* - .*Invalid API key.*from <HOST>
            ^.* - .*Rate limit exceeded.*for <HOST>
            ^.* - .*Forbidden.*from <HOST>
ignoreregex =
```

Enable fail2ban:

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Step 3: Configure UFW

```bash
# Reset and set defaults
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow services
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw limit 22/tcp comment 'SSH rate limit'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Localhost services only
sudo ufw allow from 127.0.0.1 to any port 6379 comment 'Redis'
sudo ufw allow from 127.0.0.1 to any port 5432 comment 'PostgreSQL'

# Enable firewall
sudo ufw --force enable
```

### Step 4: System Hardening

```bash
# Enable SYN cookies
sudo sysctl -w net.ipv4.tcp_syncookies=1

# Disable redirects
sudo sysctl -w net.ipv4.conf.all.accept_redirects=0
sudo sysctl -w net.ipv6.conf.all.accept_redirects=0

# Disable source routing
sudo sysctl -w net.ipv4.conf.all.accept_source_route=0

# Make permanent
sudo tee -a /etc/sysctl.conf <<EOF
net.ipv4.tcp_syncookies=1
net.ipv4.conf.all.accept_redirects=0
net.ipv6.conf.all.accept_redirects=0
net.ipv4.conf.all.accept_source_route=0
EOF
```

---

## Verification

### Check Fail2ban Status

```bash
# Overall status
sudo systemctl status fail2ban

# List active jails
sudo fail2ban-client status

# Check specific jail
sudo fail2ban-client status sshd
sudo fail2ban-client status unified-intelligence-api

# View banned IPs
sudo fail2ban-client status sshd | grep "Banned IP"

# Watch logs
sudo journalctl -u fail2ban -f
```

### Check UFW Status

```bash
# Show firewall rules
sudo ufw status verbose

# Show numbered rules (for deletion)
sudo ufw status numbered

# Check specific port
sudo ufw status | grep 22
```

### Test Protection

**Test SSH rate limiting**:
```bash
# From another machine, try multiple failed SSH attempts
ssh wrong-user@your-server  # Try 4+ times quickly
# You should get banned after 3 attempts
```

**Test firewall**:
```bash
# Test that closed ports are blocked
nc -zv localhost 3306  # MySQL (should be refused)
nc -zv localhost 27017  # MongoDB (should be refused)

# Test that open ports work
nc -zv localhost 22  # SSH (should connect)
nc -zv localhost 80  # HTTP (should connect if nginx running)
```

---

## Managing Bans

### Unban an IP

```bash
# Unban from specific jail
sudo fail2ban-client set sshd unbanip 192.168.1.100

# Unban from all jails
sudo fail2ban-client unban 192.168.1.100
```

### Add IP to Whitelist

Edit `/etc/fail2ban/jail.local` and add under `[DEFAULT]`:

```ini
[DEFAULT]
ignoreip = 127.0.0.1/8 ::1 192.168.1.0/24 YOUR_OFFICE_IP
```

Then restart:

```bash
sudo systemctl restart fail2ban
```

### Modify Ban Times

Edit `/etc/fail2ban/jail.local`:

```ini
[sshd]
bantime = 86400  # 24 hours instead of 2 hours
maxretry = 5     # 5 attempts instead of 3
```

Then restart:

```bash
sudo systemctl restart fail2ban
```

---

## Firewall Management

### Add New Rule

```bash
# Allow new port
sudo ufw allow 8080/tcp comment 'Custom app'

# Allow from specific IP
sudo ufw allow from 192.168.1.100 to any port 22

# Allow subnet
sudo ufw allow from 192.168.1.0/24
```

### Remove Rule

```bash
# Show numbered rules
sudo ufw status numbered

# Delete by number
sudo ufw delete 5

# Or delete by specification
sudo ufw delete allow 8080/tcp
```

### Disable/Enable Firewall

```bash
# Disable (WARNING: opens all ports)
sudo ufw disable

# Re-enable
sudo ufw enable
```

---

## Troubleshooting

### Locked Out of SSH

**Prevention**: Always test new firewall rules with a backup session open!

**If locked out**:
1. Access server via console (e.g., cloud provider console, physical access)
2. Run: `sudo ufw disable`
3. Fix configuration
4. Run: `sudo ufw enable`

### Fail2ban Not Banning

**Check logs**:
```bash
# View fail2ban logs
sudo tail -f /var/log/fail2ban.log

# Check if filter matches
sudo fail2ban-regex /var/log/auth.log /etc/fail2ban/filter.d/sshd.conf
```

**Common issues**:
- Log file path wrong: Check `logpath` in jail config
- Filter regex doesn't match: Test with `fail2ban-regex`
- Service not running: `sudo systemctl start fail2ban`

### UFW Not Blocking

**Check rules**:
```bash
# Verify rule exists
sudo ufw status verbose

# Check actual iptables
sudo iptables -L -n -v
```

**Test blocking**:
```bash
# From another machine
nc -zv your-server 3306  # Should be refused
```

---

## Integration with Agentic Project Builder

### Log Configuration

Ensure application logs to correct location for fail2ban:

```python
# src/main.py or logging config
import logging.config

LOGGING_CONFIG = {
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/unified-intelligence/app.log',
            'maxBytes': 10485760,
            'backupCount': 10,
        },
    },
}
```

Create log directory:

```bash
sudo mkdir -p /var/log/unified-intelligence
sudo chown $USER:$USER /var/log/unified-intelligence
```

### Application-Level Logging

Add security-relevant logging:

```python
# Log authentication failures
logger.warning(f"Authentication failed for user {username} from {request.client.host}")

# Log rate limit violations
logger.warning(f"Rate limit exceeded for {user_id} from {request.client.host}")

# Log API key failures
logger.warning(f"Invalid API key attempt from {request.client.host}")
```

These will be caught by fail2ban filter and trigger bans.

---

## Monitoring

### Daily Checks

```bash
# Check banned IPs
sudo fail2ban-client status | grep "Banned"

# Check firewall logs
sudo journalctl -u ufw -since today

# Check for attacks
sudo grep "Ban" /var/log/fail2ban.log | tail -20
```

### Set Up Alerts

**Email notifications** (requires mail setup):

Edit `/etc/fail2ban/jail.local`:

```ini
[DEFAULT]
destemail = admin@yourdomain.com
sender = fail2ban@yourserver.com
action = %(action_mwl)s
```

**Slack/Discord webhooks**:

Create `/etc/fail2ban/action.d/slack.conf` for custom notifications.

---

## Security Best Practices

1. **Keep Software Updated**:
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

2. **Monitor Logs Regularly**:
   ```bash
   sudo journalctl -u fail2ban -since "1 hour ago"
   ```

3. **Use SSH Keys** (disable password auth):
   ```bash
   # /etc/ssh/sshd_config
   PasswordAuthentication no
   ```

4. **Whitelist Known IPs**:
   Add your office/home IP to fail2ban ignoreip

5. **Review Banned IPs**:
   Check if legitimate users are getting banned

6. **Test After Changes**:
   Always keep a backup SSH session open when modifying firewall

---

## Status After Setup

After running the script, you should see:

```
✅ Fail2ban Status: Active
✅ UFW Status: Active
✅ SSH Protected: Yes (3 attempts max, rate limited)
✅ API Protected: Yes (10 attempts in 5 min)
✅ Open Ports: 22, 80, 443 only
✅ SYN Cookies: Enabled
✅ IP Redirects: Disabled
```

---

## Next Steps

After server security is configured:

1. ✅ Server hardening complete
2. ⏭ Audit git history for API keys
3. ⏭ Implement code execution sandboxing
4. ⏭ Set up AWS Secrets Manager
5. ⏭ Enable real autonomous task execution

---

**Run the setup**: `sudo ./scripts/setup_server_security.sh`
