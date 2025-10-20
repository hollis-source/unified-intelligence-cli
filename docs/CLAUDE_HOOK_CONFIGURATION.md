# Claude Code Hook Configuration

**Date:** October 17, 2025
**Purpose:** Documentation for managing Claude Code hooks

---

## Overview

Claude Code supports custom hooks that execute at various points in the workflow:
- **PostToolUse hooks:** Trigger after Write/Edit/MultiEdit tools complete
- **PrePromptSubmit hooks:** Trigger before processing user prompts
- **Custom hooks:** User-defined workflow automation

Hooks are located in `.claude/hooks/` directory.

---

## Available Hooks

### Active Hooks ✅

**1. ultrathink_submit.py**
- **Trigger:** PrePromptSubmit
- **Purpose:** Adds "ultrathink" directive to prompts
- **Status:** ✅ ACTIVE
- **Impact:** Enhances AI reasoning quality

**2. continuous_improvement_enforcer.py**
- **Trigger:** PostToolUse
- **Purpose:** Enforces code quality and best practices
- **Status:** ✅ ACTIVE
- **Impact:** Maintains code standards

### Disabled Hooks 🚫

**3. autocommit_post.py.disabled**
- **Trigger:** PostToolUse (after Write/Edit)
- **Purpose:** Automatic git commits with AI-generated messages
- **Status:** 🚫 DISABLED (Oct 17, 2025)
- **Reason:** Creates excessive commit noise in git history
- **To Re-enable:** `mv .claude/hooks/autocommit_post.py.disabled .claude/hooks/autocommit_post.py`

**4. auto_delegate.py.disabled**
- **Trigger:** Custom
- **Purpose:** Automatic task delegation
- **Status:** 🚫 DISABLED
- **To Re-enable:** `mv .claude/hooks/auto_delegate.py.disabled .claude/hooks/auto_delegate.py`

**5. delegation_watcher.py.disabled**
- **Trigger:** Custom
- **Purpose:** Monitor delegation patterns
- **Status:** 🚫 DISABLED
- **To Re-enable:** `mv .claude/hooks/delegation_watcher.py.disabled .claude/hooks/delegation_watcher.py`

---

## Auto-Commit Hook Details

### Why It Was Disabled

**Problem:**
- Created 5+ small commits per session
- Fragmented logical work units
- Made git history difficult to review
- Example: `chore: update main.py`, `test: update test_executor.py`, etc.

**Impact:**
- Git history noise: Medium-High
- Commit message quality: Low (generic fallbacks)
- Batching issues: 30-second window insufficient for complex tasks

### Configuration Options

If you want to re-enable with better behavior:

**Option 1: Increase Batch Window**
```bash
export AUTOCOMMIT_BATCH_WINDOW=300  # 5 minutes
export AUTOCOMMIT_MAX_DIFF_SIZE=50000  # Larger diffs
```

**Option 2: Disable via Environment**
```bash
export AUTOCOMMIT_DISABLE=1
```

**Option 3: Rename to .disabled** (Current approach)
```bash
mv .claude/hooks/autocommit_post.py .claude/hooks/autocommit_post.py.disabled
```

### Environment Variables

```bash
# Disable hook entirely
AUTOCOMMIT_DISABLE=1

# Batching window (seconds)
AUTOCOMMIT_BATCH_WINDOW=30  # Default: 30s

# Max diff size (characters)
AUTOCOMMIT_MAX_DIFF_SIZE=10000  # Default: 10000

# Log level (DEBUG, INFO, WARNING, ERROR)
AUTOCOMMIT_LOG_LEVEL=INFO  # Default: INFO
```

### Logs

Auto-commit logs are written to:
```
~/.claude/autocommit.log
```

View recent activity:
```bash
tail -50 ~/.claude/autocommit.log
```

---

## Hook Development Guidelines

### Creating a Custom Hook

1. **Create hook file** in `.claude/hooks/`
```python
#!/usr/bin/env python3
"""
MyHook - Brief description

Trigger: PostToolUse / PrePromptSubmit
"""
import sys
import json

def main():
    # Read hook input from stdin
    hook_input = json.loads(sys.stdin.read())
    
    # Your hook logic here
    
    # Exit successfully
    sys.exit(0)

if __name__ == '__main__':
    main()
```

2. **Make executable**
```bash
chmod +x .claude/hooks/my_hook.py
```

3. **Test hook**
```bash
echo '{"tool_input": {"file_path": "test.py"}}' | .claude/hooks/my_hook.py
```

### Best Practices

✅ **DO:**
- Handle exceptions gracefully
- Log to `~/.claude/` directory
- Use environment variables for configuration
- Exit with status 0 (don't fail)
- Document hook purpose and behavior

❌ **DON'T:**
- Block for extended periods
- Make network calls without timeouts
- Modify files without safety checks
- Fail loudly (breaks Claude Code workflow)
- Create excessive commits/noise

---

## Troubleshooting

### Hook Not Triggering

1. Check file permissions:
```bash
ls -la .claude/hooks/
```
Ensure execute bit is set (`-rwxrwxr-x`)

2. Check file extension:
```bash
# Should NOT have .disabled extension
ls .claude/hooks/*.disabled
```

3. Check logs:
```bash
tail -50 ~/.claude/autocommit.log
tail -50 ~/.claude/hooks.log  # If exists
```

### Hook Causing Issues

**Quick Fix: Disable temporarily**
```bash
mv .claude/hooks/problematic_hook.py .claude/hooks/problematic_hook.py.disabled
```

**Debug:**
```bash
# Test hook in isolation
echo '{"test": "input"}' | .claude/hooks/problematic_hook.py
```

---

## Recommendation

**Current Configuration (Oct 17, 2025):**

✅ **Keep Enabled:**
- `ultrathink_submit.py` - Enhances reasoning
- `continuous_improvement_enforcer.py` - Maintains quality

🚫 **Keep Disabled:**
- `autocommit_post.py.disabled` - Too noisy for git history
- `auto_delegate.py.disabled` - Not needed for current workflow
- `delegation_watcher.py.disabled` - Not needed for current workflow

**Manual Commits Preferred:**
- Better commit message quality
- Logical grouping of changes
- Clean git history
- Full developer control

---

## Related Documentation

- [Claude Code Hooks](https://docs.claude.com/claude-code/hooks)
- [Git Best Practices](../CLAUDE.md#clean-agile-practices)
- [Session Summary](./SESSION_SUMMARY_OCT17_2025.md)

---

**Last Updated:** October 17, 2025
**Status:** Autocommit hook disabled for cleaner git history
