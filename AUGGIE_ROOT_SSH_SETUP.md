# Auggie MCP Root SSH Setup

## Current Status

The Auggie MCP server has been modified to execute commands as `root@157.90.66.183` via SSH. This allows running sudo-requiring commands without explicitly using sudo.

## Configuration Changes

**Modified**: `/home/ui-cli_jake/.mcp-servers/auggie-mcp-server.js`

- Added SSH_HOST: `root@157.90.66.183`
- Added SSH_IDENTITY: `/home/ui-cli_jake/.ssh/id_ed25519`
- All commands now execute via: `ssh root@157.90.66.183 "<command>"`

## Required: Enable Root SSH Access

Currently, SSH as root is **not enabled**. You need to:

### Option 1: Enable Root SSH with Key (Recommended)

```bash
# 1. Copy public key to root's authorized_keys
sudo mkdir -p /root/.ssh
sudo chmod 700 /root/.ssh
sudo cp ~/.ssh/id_ed25519.pub /root/.ssh/authorized_keys
sudo chmod 600 /root/.ssh/authorized_keys
sudo chown -R root:root /root/.ssh

# 2. Test SSH access
ssh -i ~/.ssh/id_ed25519 root@157.90.66.183 "whoami"
# Should output: root
```

### Option 2: Alternative - Use sudo wrapper (if root SSH not desired)

If you don't want to enable root SSH, I can modify Auggie MCP to use local execution with sudo wrapper instead.

## Testing After Setup

Once root SSH is enabled, test with:

```bash
# Test basic SSH
ssh -i ~/.ssh/id_ed25519 root@157.90.66.183 "whoami && pwd"

# Test with working directory
ssh -i ~/.ssh/id_ed25519 root@157.90.66.183 "cd /home/ui-cli_jake/unified-intelligence-cli && pwd"

# Test sudo-requiring command (no sudo needed)
ssh -i ~/.ssh/id_ed25519 root@157.90.66.183 "cd /home/ui-cli_jake/unified-intelligence-cli && cat /etc/hosts | tail -3"
```

## Using Auggie After Setup

Once configured, you can use Auggie MCP tools that require root without sudo:

```javascript
// Example: Test security stack (requires sudo for /etc/hosts)
mcp__auggie__auggie_with_gpt5({
  instruction: "Add grafana.dev.local to /etc/hosts, then test the security-hardened Docker Compose stack"
})
```

## Troubleshooting

### Permission Denied (publickey)

This means root SSH isn't configured yet. Run the setup commands above.

### SSH Works But Wrong Directory

The MCP server automatically does `cd /home/ui-cli_jake/unified-intelligence-cli` before executing commands.

### Still Need Sudo

If you still need sudo after setup, the SSH connection isn't working as root. Verify with:
```bash
ssh -i ~/.ssh/id_ed25519 root@157.90.66.183 "whoami"
```

## Rollback to Local Execution

If you want to revert to local (non-root) execution, restore the original:

```javascript
// Change in auggie-mcp-server.js:
const sshCmd = `cd "${workingDir}" && ${auggieCmd}`;  // Remove SSH wrapper
```

## Security Note

Enabling root SSH with key-based authentication is secure IF:
- ✅ Private key is protected (600 permissions)
- ✅ Only authorized keys in /root/.ssh/authorized_keys
- ✅ PasswordAuthentication is disabled in /etc/ssh/sshd_config
- ✅ Server is behind firewall (only trusted IPs can access SSH)

---

**Next Step**: Run the setup commands in Option 1 to enable root SSH access.
