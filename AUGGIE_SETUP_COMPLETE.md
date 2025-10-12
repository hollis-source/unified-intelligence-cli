# Auggie MCP Integration - Setup Complete ✅

**Date**: 2025-10-07
**Status**: Ready for use (requires Claude Code restart)

---

## Installation Summary

### ✅ Completed Steps

1. **Node.js 22.20.0** - Installed via nvm
   - Location: `/home/ui-cli_jake/.nvm/versions/node/v22.20.0`
   - npm: v10.9.3

2. **Auggie CLI 0.5.7** - Installed globally
   - Location: `/home/ui-cli_jake/.nvm/versions/node/v22.20.0/bin/auggie`
   - Authenticated: ✅ (user completed OAuth)

3. **MCP Server** - Created and configured
   - Server script: `~/.mcp-servers/auggie-mcp-server.js`
   - Dependencies: Installed (@modelcontextprotocol/sdk)
   - Configuration: `~/.claude/config.json`

4. **Claude Code Configuration** - Ready
   - MCP server registered as "auggie"
   - Default workspace: `/home/ui-cli_jake/unified-intelligence-cli`
   - Auggie path: `/home/ui-cli_jake/.nvm/versions/node/v22.20.0/bin/auggie`

---

## 🔄 NEXT STEP: Restart Claude Code (IN NORMAL MODE)

**CRITICAL**: Claude Code must be restarted **WITHOUT sandbox mode** to load MCP servers.

### ⚠️ Sandbox Mode Issue

**Problem**: If Claude Code is running with `--dangerously-skip-permissions` flag (sandbox mode), MCP servers **cannot load**.

**Why**:
- Sandbox mode blocks external process spawning (security restriction)
- MCP servers require spawning: `bash → node → auggie-mcp-server.js`
- stdio communication with subprocesses is restricted in sandbox

**Check Current Mode**:
```bash
ps aux | grep claude | grep -v grep
# If you see: --dangerously-skip-permissions
# Then: You're in sandbox mode (MCP won't work)
```

### How to Restart (Normal Mode)

**IMPORTANT**: Start Claude Code **without** the `--dangerously-skip-permissions` flag

1. Exit current Claude Code session (Ctrl+D or type `exit`)
2. Reconnect to server: `ssh ui-cli_jake@157.90.66.183`
3. Start Claude Code in **normal mode**:
   ```bash
   claude
   # OR
   claude-code
   # (Do NOT use --dangerously-skip-permissions flag)
   ```

### After Restart

Ask Claude Code: **"What MCP tools do you have available?"**

You should see:
- ✅ `auggie_execute`
- ✅ `auggie_with_gpt5`
- ✅ `auggie_with_claude`
- ✅ `auggie_session_list`

---

## 🚀 How to Use Auggie

### Quick Examples

**1. Get GPT-5's Perspective**
```
Ask Claude Code: "Use auggie with GPT-5 to review the coordinator.py refactoring"
```

**2. Delegate Complex Refactoring**
```
Ask Claude Code: "Use auggie to add comprehensive JSDoc comments to all functions"
```

**3. Multi-Model Comparison**
```
Ask Claude Code: "Compare your approach vs GPT-5's approach for HTN decomposition optimization"
```

**4. Parallel Work**
```
Ask Claude Code: "I'll design the architecture, have auggie implement the Prometheus metric endpoints"
```

---

## 🎯 Top Use Cases for Unified Intelligence CLI

### 1. **Production Readiness Validation**
- You: Review architecture and SOLID principles
- Auggie (GPT-5): Review from fresh perspective
- Result: 360° validation before deployment

### 2. **Documentation Generation**
- You: Focus on complex implementations
- Auggie: Generate comprehensive docs for all modules
- Result: Complete documentation without context overhead

### 3. **Multi-Model Code Review**
- You: Analyze architecture compliance
- Auggie (GPT-5): Analyze from different angle
- Result: Synthesis of multiple expert opinions

### 4. **Integration Test Expansion**
- You: Design test architecture
- Auggie: Implement 10+ test variants
- Result: Faster test coverage

### 5. **Monitoring Dashboard Setup** (Current P1 Priority)
- You: Design Prometheus/Grafana architecture
- Auggie: Implement metric endpoints and dashboards
- Result: Parallel work on production deployment tasks

---

## 📋 Available MCP Tools

### `auggie_execute`
**Full control over auggie execution**

Parameters:
- `instruction` (required): Task for auggie
- `workingDir`: Directory path (default: project root)
- `model`: "sonnet4", "sonnet4.5", or "gpt5"
- `quiet`: Hide tool details (default: false)
- `compact`: Compact logging (default: false)
- `maxTurns`: Limit agentic turns

Example:
```
"Use auggie to refactor all error handling with model sonnet4.5"
```

### `auggie_with_gpt5`
**Quick GPT-5 access**

Parameters:
- `instruction` (required): Task for GPT-5
- `workingDir`: Directory path

Example:
```
"Ask GPT-5 via auggie to suggest optimization strategies for our HTN implementation"
```

### `auggie_with_claude`
**Claude Sonnet 4.5 via auggie**

Parameters:
- `instruction` (required): Task for Claude 4.5
- `workingDir`: Directory path

Example:
```
"Have auggie's Claude 4.5 analyze the database schema design"
```

### `auggie_session_list`
**View recent auggie sessions**

Parameters:
- `limit`: Number of sessions (default: 5)

Example:
```
"Show me the last 10 auggie sessions"
```

---

## 🛠️ Configuration Details

### MCP Server Configuration
```json
{
  "mcpServers": {
    "auggie": {
      "command": "bash",
      "args": ["-c", "export NVM_DIR=\"$HOME/.nvm\" && ..."],
      "env": {
        "AUGGIE_WORKSPACE": "/home/ui-cli_jake/unified-intelligence-cli",
        "AUGGIE_PATH": "/home/ui-cli_jake/.nvm/versions/node/v22.20.0/bin/auggie"
      }
    }
  }
}
```

### File Locations
- **MCP Server**: `~/.mcp-servers/auggie-mcp-server.js`
- **Package.json**: `~/.mcp-servers/package.json`
- **Config**: `~/.claude/config.json`
- **Auggie CLI**: `~/.nvm/versions/node/v22.20.0/bin/auggie`
- **NVM**: `~/.nvm/`

---

## 🔍 Troubleshooting

### If MCP Server Doesn't Load

**1. Check config syntax**
```bash
cat ~/.claude/config.json | python3 -m json.tool
```

**2. Test MCP server manually**
```bash
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && node ~/.mcp-servers/auggie-mcp-server.js
# Should output: "Auggie MCP Server running"
# Press Ctrl+C to exit
```

**3. Verify auggie works**
```bash
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && auggie --version
# Should show: 0.5.7
```

### If Auggie Authentication Fails

```bash
export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && auggie login
```

### If Dependencies Missing

```bash
cd ~/.mcp-servers && npm install
```

---

## 📊 Strategic Benefits

### Multi-Model Capabilities
- **Claude Sonnet 4/4.5**: Complex reasoning, architectural decisions
- **GPT-5**: Alternative perspectives, code optimization
- **Multiple viewpoints**: Reduces blind spots, improves quality

### Delegation & Parallelization
- **Context preservation**: Save your context for complex work
- **Parallel execution**: Work on architecture while auggie implements
- **Faster delivery**: 2-3x speed on multi-task projects

### Quality Assurance
- **Second opinions**: Catch issues you might miss
- **Multi-model review**: Different AI perspectives on same code
- **Evidence-based decisions**: Multiple data points for critical choices

---

## 🎓 Best Practices

### When to Use Auggie

**✅ Perfect for:**
- Multi-file refactoring (>10 files)
- Repetitive well-defined tasks
- Getting GPT-5's perspective
- Second opinion on complex code
- Parallel work (architecture + implementation)
- Model comparison requests

**⚠️ Handle yourself:**
- Simple quick tasks (<5 min)
- Requires conversation context
- Needs nuanced understanding
- Ambiguous requirements
- User specifically asking you

### Workflow Pattern

```
User Request
    ↓
Analyze & Decide
    ↓
┌───────────────────┐
│   Complex/Large   │ → Delegate to Auggie
│   Simple/Context  │ → Handle yourself
└───────────────────┘
    ↓
Review Auggie's Work
    ↓
Synthesize & Present
```

---

## 📝 Next Steps After Restart

1. **Verify MCP Tools**: Ask "What MCP tools do you have available?"
2. **Test Simple Task**: "Use auggie to list files in this directory"
3. **Test GPT-5**: "Ask GPT-5 via auggie about code optimization strategies"
4. **Production Work**: Use for current P1 priorities (monitoring dashboard, docs)

---

## 🎉 Installation Complete!

**Status**: ✅ Ready for use after Claude Code restart

**Benefits Unlocked**:
- Multi-model coding (Claude 4/4.5 + GPT-5)
- Parallel execution capabilities
- Context preservation
- Code quality through multiple perspectives

**Ready to restart Claude Code and start using auggie!**

---

**Setup completed**: 2025-10-07
**Setup time**: ~15 minutes
**Installed by**: Claude (autonomous setup)
