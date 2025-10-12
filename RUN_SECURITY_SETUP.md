# IMMEDIATE ACTION REQUIRED: Run Security Setup

## Step 1: Install fail2ban and UFW

Run this command now:

```bash
sudo ./scripts/setup_server_security.sh
```

**This will**:
- Install fail2ban (intrusion prevention)
- Install/configure UFW firewall
- Set up SSH protection (rate limiting + fail2ban)
- Enable system hardening
- Takes ~2 minutes

**Password required**: You'll need to enter your sudo password

---

## Step 2: Verify Setup

After running the script, verify with:

```bash
# Check fail2ban
sudo systemctl status fail2ban

# Check UFW
sudo ufw status verbose

# Should show:
# - fail2ban: active
# - UFW: active
# - Ports 22, 80, 443 open
```

---

## After Server Security Complete

The automation will continue with:

1. ✅ Server hardening (fail2ban + ufw)
2. ⏭ Git history audit for leaked secrets
3. ⏭ Real code execution (no mocks)
4. ⏭ Autonomous agent capabilities

**Run the command above when ready.**
