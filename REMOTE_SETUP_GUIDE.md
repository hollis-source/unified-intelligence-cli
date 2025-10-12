# Auggie MCP Setup on Remote Server
## Complete Installation Guide for root@157.90.66.183

This guide assumes you're running Claude Code in an SSH session on your remote server.

---

## 📋 Overview

You'll install everything ON the remote server:
- ✅ Node.js 22
- ✅ Auggie CLI
- ✅ MCP server script
- ✅ Claude Code configuration

Since Claude Code runs on the remote, the MCP server will also run there (no SSH overhead!).

---

## 🚀 Step-by-Step Installation

### Step 1: SSH to Your Remote Server

```bash
ssh root@157.90.66.183
```

### Step 2: Check if Node.js is Installed

```bash
node --version
npm --version
```

**If you see versions displayed:** Skip to Step 4
**If you see "command not found":** Continue to Step 3

### Step 3: Install Node.js 22 (if needed)

#### For Ubuntu/Debian:

```bash
# Update package list
apt update

# Install curl if not present
apt install -y curl

# Add Node.js 22 repository
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -

# Install Node.js
apt install -y nodejs

# Verify installation
node --version  # Should show v22.x.x
npm --version   # Should show 10.x.x
```

#### For CentOS/RHEL:

```bash
# Update package list
yum update

# Install curl if not present
yum install -y curl

# Add Node.js 22 repository
curl -fsSL https://rpm.nodesource.com/setup_22.x | bash -

# Install Node.js
yum install -y nodejs

# Verify installation
node --version
npm --version
```

#### For Other Systems:

Visit: https://nodejs.org/en/download/package-manager

### Step 4: Install Auggie CLI Globally

```bash
# Install auggie
npm install -g @augmentcode/auggie

# Verify installation
auggie --version
# Should show: 0.5.7 (or newer)

# Check auggie location
which auggie
# Should show: /usr/local/bin/auggie or similar
```

### Step 5: Authenticate Auggie

```bash
# Start authentication
auggie login
```

**You'll see:**
```
🔐 Starting Augment authentication...

🌐 Opening authentication page in your browser...
Please complete authentication in your browser:

https://auth.augmentcode.com/authorize?response_type=code&...

After authenticating, you will receive a JSON response.
Copy the entire JSON response and paste it below.

Paste the JSON response here:
```

**Important Steps:**

1. **Copy the URL** from the terminal
2. **Open it in your browser** (on your local machine)
3. **Log in to Augment Code** (or create account)
4. **You'll receive a JSON response** like:
   ```json
   {"code":"...", "state":"...", "tenant_url":"..."}
   ```
5. **Copy the ENTIRE JSON** (including the curly braces)
6. **Paste it into the terminal** and press Enter

**Verify authentication:**
```bash
# Check if authenticated
auggie token print

# You should see:
# 🔑 Augment authentication token:
# TOKEN={...}
```

### Step 6: Test Auggie

```bash
# Test auggie works
cd /root/projects  # or your main working directory
auggie --print "list files in this directory"
```

**Expected output:**
- Should list files successfully
- If it works, auggie is ready!

### Step 7: Create MCP Server Directory

```bash
# Create directory for MCP servers
mkdir -p ~/.mcp-servers

# Navigate to it
cd ~/.mcp-servers
```

### Step 8: Create MCP Server Script

Create the MCP server file:

```bash
cat > ~/.mcp-servers/auggie-mcp-server.js << 'EOFMCP'
#!/usr/bin/env node

/**
 * Auggie MCP Server for Remote Development
 * This runs locally on the same server as Claude Code
 * No SSH needed since everything is local!
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// Configuration from environment
const DEFAULT_WORKSPACE = process.env.AUGGIE_WORKSPACE || '/root/projects';
const AUGGIE_PATH = process.env.AUGGIE_PATH || 'auggie';

/**
 * Execute auggie command locally
 */
async function executeAuggie(workingDir, instruction, options = {}) {
  const {
    model = null,
    print = true,
    quiet = false,
    outputFormat = 'text',
    compact = false,
    maxTurns = null,
  } = options;

  // Build auggie command
  let cmd = `cd "${workingDir}" && ${AUGGIE_PATH}`;

  if (print) cmd += ' --print';
  if (quiet) cmd += ' --quiet';
  if (compact) cmd += ' --compact';
  if (model) cmd += ` --model ${model}`;
  if (outputFormat === 'json') cmd += ' --output-format json';
  if (maxTurns) cmd += ` --max-turns ${maxTurns}`;

  // Escape instruction for shell
  const escapedInstruction = instruction.replace(/'/g, "'\\''");
  cmd += ` '${escapedInstruction}'`;

  try {
    const { stdout, stderr } = await execAsync(cmd, {
      maxBuffer: 10 * 1024 * 1024, // 10MB buffer
      timeout: 300000, // 5 minute timeout
      shell: '/bin/bash',
    });

    return {
      success: true,
      stdout: stdout.trim(),
      stderr: stderr.trim(),
      outputFormat,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
      stdout: error.stdout || '',
      stderr: error.stderr || '',
    };
  }
}

/**
 * Create and configure the MCP server
 */
const server = new Server(
  {
    name: 'auggie-local',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * List available tools
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'auggie_execute',
        description: 'Execute an auggie command with full control. Auggie is an agentic coding CLI that can analyze, edit, and refactor code using Claude Sonnet 4, 4.5, or GPT-5. Use this when you want to delegate complex coding tasks or get a different AI model\'s perspective.',
        inputSchema: {
          type: 'object',
          properties: {
            instruction: {
              type: 'string',
              description: 'The instruction for auggie (e.g., "refactor this function to be more efficient", "add error handling to all API calls")',
            },
            workingDir: {
              type: 'string',
              description: 'Working directory path (absolute path)',
              default: DEFAULT_WORKSPACE,
            },
            model: {
              type: 'string',
              enum: ['sonnet4', 'sonnet4.5', 'gpt5'],
              description: 'AI model to use. sonnet4=Claude Sonnet 4 (default), sonnet4.5=Claude Sonnet 4.5 (latest), gpt5=OpenAI GPT-5',
            },
            outputFormat: {
              type: 'string',
              enum: ['text', 'json'],
              description: 'Output format',
              default: 'text',
            },
            quiet: {
              type: 'boolean',
              description: 'Only show final output (hide tool call details)',
              default: false,
            },
            compact: {
              type: 'boolean',
              description: 'Use compact logging for cleaner output',
              default: false,
            },
            maxTurns: {
              type: 'number',
              description: 'Maximum number of agentic turns (limits complexity)',
            },
          },
          required: ['instruction'],
        },
      },
      {
        name: 'auggie_with_gpt5',
        description: 'Quick access to GPT-5 via auggie for tasks where OpenAI models might excel. Uses quiet mode for clean output. Perfect for getting a different AI\'s perspective on code problems.',
        inputSchema: {
          type: 'object',
          properties: {
            instruction: {
              type: 'string',
              description: 'The instruction for GPT-5',
            },
            workingDir: {
              type: 'string',
              description: 'Working directory path',
              default: DEFAULT_WORKSPACE,
            },
          },
          required: ['instruction'],
        },
      },
      {
        name: 'auggie_with_claude',
        description: 'Execute auggie with Claude Sonnet 4.5 (latest Claude model). Useful for complex reasoning and detailed analysis.',
        inputSchema: {
          type: 'object',
          properties: {
            instruction: {
              type: 'string',
              description: 'The instruction for Claude Sonnet 4.5',
            },
            workingDir: {
              type: 'string',
              description: 'Working directory path',
              default: DEFAULT_WORKSPACE,
            },
          },
          required: ['instruction'],
        },
      },
      {
        name: 'auggie_session_list',
        description: 'List recent auggie sessions. Useful for continuing previous work or reviewing what auggie has done.',
        inputSchema: {
          type: 'object',
          properties: {
            limit: {
              type: 'number',
              description: 'Number of sessions to show',
              default: 5,
            },
          },
        },
      },
    ],
  };
});

/**
 * Handle tool calls
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'auggie_execute': {
        const result = await executeAuggie(
          args.workingDir || DEFAULT_WORKSPACE,
          args.instruction,
          {
            model: args.model,
            outputFormat: args.outputFormat || 'text',
            quiet: args.quiet || false,
            compact: args.compact || false,
            maxTurns: args.maxTurns,
          }
        );

        if (!result.success) {
          return {
            content: [
              {
                type: 'text',
                text: `Error executing auggie:\n${result.error}\n\nStderr: ${result.stderr}\n\nStdout: ${result.stdout}`,
              },
            ],
            isError: true,
          };
        }

        // Parse JSON output if requested
        let output = result.stdout;
        if (args.outputFormat === 'json' && output) {
          try {
            const parsed = JSON.parse(result.stdout);
            output = JSON.stringify(parsed, null, 2);
          } catch (e) {
            // Keep as-is if not valid JSON
          }
        }

        return {
          content: [
            {
              type: 'text',
              text: output || '(no output)',
            },
          ],
        };
      }

      case 'auggie_with_gpt5': {
        const result = await executeAuggie(
          args.workingDir || DEFAULT_WORKSPACE,
          args.instruction,
          {
            model: 'gpt5',
            quiet: true,
            print: true,
          }
        );

        if (!result.success) {
          return {
            content: [
              {
                type: 'text',
                text: `Error executing auggie with GPT-5:\n${result.error}`,
              },
            ],
            isError: true,
          };
        }

        return {
          content: [
            {
              type: 'text',
              text: `GPT-5 via Auggie:\n\n${result.stdout}`,
            },
          ],
        };
      }

      case 'auggie_with_claude': {
        const result = await executeAuggie(
          args.workingDir || DEFAULT_WORKSPACE,
          args.instruction,
          {
            model: 'sonnet4.5',
            quiet: true,
            print: true,
          }
        );

        if (!result.success) {
          return {
            content: [
              {
                type: 'text',
                text: `Error executing auggie with Claude Sonnet 4.5:\n${result.error}`,
              },
            ],
            isError: true,
          };
        }

        return {
          content: [
            {
              type: 'text',
              text: `Claude Sonnet 4.5 via Auggie:\n\n${result.stdout}`,
            },
          ],
        };
      }

      case 'auggie_session_list': {
        const limit = args.limit || 5;
        const cmd = `auggie session list --limit ${limit}`;

        const { stdout, stderr } = await execAsync(cmd);

        return {
          content: [
            {
              type: 'text',
              text: `Auggie Sessions:\n\n${stdout}`,
            },
          ],
        };
      }

      default:
        return {
          content: [
            {
              type: 'text',
              text: `Unknown tool: ${name}`,
            },
          ],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

/**
 * Start the server
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Auggie MCP Server running');
  console.error(`Default workspace: ${DEFAULT_WORKSPACE}`);
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
EOFMCP

# Make it executable
chmod +x ~/.mcp-servers/auggie-mcp-server.js
```

### Step 9: Create package.json for MCP Server

```bash
cat > ~/.mcp-servers/package.json << 'EOFPKG'
{
  "name": "auggie-mcp-server",
  "version": "1.0.0",
  "type": "module",
  "description": "MCP server for Auggie CLI",
  "main": "auggie-mcp-server.js",
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0"
  }
}
EOFPKG
```

### Step 10: Install MCP Server Dependencies

```bash
cd ~/.mcp-servers
npm install
```

**Expected output:**
```
added X packages in Xs
```

### Step 11: Test MCP Server

```bash
# Quick test (should show startup message)
node ~/.mcp-servers/auggie-mcp-server.js
# Should output: "Auggie MCP Server running"
# Press Ctrl+C to exit
```

### Step 12: Configure Claude Code

Create or edit Claude Code configuration:

```bash
# Create .claude directory if it doesn't exist
mkdir -p ~/.claude

# Create or edit config.json
cat > ~/.claude/config.json << 'EOFCONFIG'
{
  "mcpServers": {
    "auggie": {
      "command": "node",
      "args": [
        "/root/.mcp-servers/auggie-mcp-server.js"
      ],
      "env": {
        "AUGGIE_WORKSPACE": "/root/projects",
        "AUGGIE_PATH": "auggie"
      }
    }
  }
}
EOFCONFIG
```

**Important:**
- Replace `/root/projects` with your actual main working directory
- If auggie is not in PATH, specify full path like `/usr/local/bin/auggie`

### Step 13: Verify Configuration

```bash
# Check the config file
cat ~/.claude/config.json

# Verify paths are correct
ls -la ~/.mcp-servers/auggie-mcp-server.js
which auggie
```

### Step 14: Restart Claude Code

```bash
# Exit your current Claude Code session
exit  # or Ctrl+D

# Reconnect via SSH
ssh root@157.90.66.183

# Start Claude Code
claude-code  # or however you start it

# Claude Code should now load the MCP server
```

---

## ✅ Verification Steps

Once Claude Code restarts, verify the MCP server is working:

### Check 1: MCP Server Loaded

Look for startup messages about MCP servers when Claude Code starts.

### Check 2: Ask Claude Code

Ask me (Claude Code): "What MCP tools do you have available?"

I should respond with tools like:
- `auggie_execute`
- `auggie_with_gpt5`
- `auggie_with_claude`
- `auggie_session_list`

### Check 3: Test a Simple Command

Ask me: "Use auggie to list files in the current directory"

I should use the `auggie_execute` tool and return results.

### Check 4: Test GPT-5

Ask me: "Use auggie with GPT-5 to suggest improvements to [some file]"

I should use the `auggie_with_gpt5` tool and return GPT-5's suggestions.

---

## 🔧 Troubleshooting

### Issue: "auggie: command not found"

**Solution:**
```bash
# Find where auggie is installed
npm list -g @augmentcode/auggie

# Update config with full path
# Edit ~/.claude/config.json:
"AUGGIE_PATH": "/usr/local/bin/auggie"
```

### Issue: "MCP server not loading"

**Solution:**
```bash
# Check config syntax
cat ~/.claude/config.json | python3 -m json.tool

# Test MCP server manually
node ~/.mcp-servers/auggie-mcp-server.js
# Should output startup message
```

### Issue: "Authentication expired"

**Solution:**
```bash
# Re-authenticate auggie
auggie login

# Verify
auggie token print
```

### Issue: "Cannot find module @modelcontextprotocol/sdk"

**Solution:**
```bash
# Reinstall dependencies
cd ~/.mcp-servers
npm install
```

### Issue: "Permission denied"

**Solution:**
```bash
# Make script executable
chmod +x ~/.mcp-servers/auggie-mcp-server.js

# Check permissions
ls -la ~/.mcp-servers/
```

---

## 📝 Configuration Customization

### Multiple Working Directories

If you work in different directories, you can specify per-tool:

```json
{
  "mcpServers": {
    "auggie-project1": {
      "command": "node",
      "args": ["/root/.mcp-servers/auggie-mcp-server.js"],
      "env": {
        "AUGGIE_WORKSPACE": "/root/project1"
      }
    },
    "auggie-project2": {
      "command": "node",
      "args": ["/root/.mcp-servers/auggie-mcp-server.js"],
      "env": {
        "AUGGIE_WORKSPACE": "/root/project2"
      }
    }
  }
}
```

### Debugging Mode

Add debugging to see what's happening:

```json
{
  "mcpServers": {
    "auggie": {
      "command": "node",
      "args": ["/root/.mcp-servers/auggie-mcp-server.js"],
      "env": {
        "AUGGIE_WORKSPACE": "/root/projects",
        "NODE_ENV": "development",
        "DEBUG": "mcp:*"
      }
    }
  }
}
```

---

## 🎯 Quick Reference

### Installed Locations

- **Auggie CLI**: `/usr/local/bin/auggie` (or `which auggie`)
- **MCP Server**: `~/.mcp-servers/auggie-mcp-server.js`
- **Config File**: `~/.claude/config.json`
- **Auggie Config**: `~/.augment/`

### Useful Commands

```bash
# Check auggie
auggie --version
auggie token print

# Test MCP server
node ~/.mcp-servers/auggie-mcp-server.js

# View config
cat ~/.claude/config.json

# Restart Claude Code
exit  # then reconnect

# Check logs
journalctl -u claude-code  # if running as service
```

---

## 🚀 You're Done!

After completing these steps, you'll have:
- ✅ Auggie CLI installed and authenticated
- ✅ MCP server running when Claude Code starts
- ✅ Access to GPT-5 via auggie tools
- ✅ Full multi-model coding capabilities

**Next:** Start using auggie through me (Claude Code) by asking questions like:
- "Use auggie with GPT-5 to review this code"
- "Have auggie refactor this module"
- "Get auggie's opinion on this architecture"

---

## 📚 What You Can Now Do

1. **Delegate Complex Tasks**
   - "Use auggie to refactor the entire auth module"

2. **Get GPT-5's Perspective**
   - "Ask GPT-5 (via auggie) how to optimize this algorithm"

3. **Compare Approaches**
   - "Have both you and auggie suggest improvements"

4. **Multi-Step Refactoring**
   - "Use auggie to modernize all the API endpoints"

Enjoy your multi-model development environment! 🎉
