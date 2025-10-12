# Automated Commit System

**Automatic git commits powered by AI** 🤖

---

## What is this?

A background automation system that **automatically commits your code changes** as you work, freeing you from manual git operations.

**No more:**
- ❌ Typing `git add .`
- ❌ Writing commit messages
- ❌ Running `git commit -m "..."`
- ❌ Forgetting to commit

**Instead:**
- ✅ Edit files normally
- ✅ Commits happen automatically
- ✅ AI generates quality messages
- ✅ Focus on coding, not git

---

## Quick Start

### 1. Check if it's installed

```bash
# Check hook exists
ls -l .claude/hooks/autocommit_post.py

# Check hook is registered
cat .claude/settings.json | grep PostToolUse
```

If both exist, you're ready! If not, see [Installation](#installation).

### 2. Test it

```bash
# Create a test file
echo "test content" > test_autocommit.txt

# Wait 30 seconds (batching window)
sleep 30

# Check if commit was created
git log -1

# Check the log
tail -5 ~/.claude/autocommit.log
```

**Expected:** New commit with message like "chore: update test_autocommit.txt"

### 3. Use it

Just work normally! Commits happen automatically after every file edit.

---

## How It Works

```
You edit a file → 30s wait → AI analyzes changes → Commit created
```

**Example:**
```bash
14:30:00 - You edit file1.py
14:30:15 - You edit file2.py
14:30:25 - You edit file3.py
14:30:55 - COMMIT (all 3 files together)
```

**Why 30 seconds?** To batch related changes instead of creating dozens of tiny commits.

---

## Configuration

### Disable temporarily

```bash
export AUTOCOMMIT_DISABLE=1
# ... do work ...
unset AUTOCOMMIT_DISABLE
```

### Change batch window

```bash
export AUTOCOMMIT_BATCH_WINDOW=60  # Wait 60 seconds instead of 30
```

### Enable debug logging

```bash
export AUTOCOMMIT_LOG_LEVEL=DEBUG
tail -f ~/.claude/autocommit.log
```

---

## Monitoring

### View recent activity

```bash
tail -20 ~/.claude/autocommit.log
```

### Watch in real-time

```bash
tail -f ~/.claude/autocommit.log
```

### Check recent commits

```bash
git log --oneline -10
```

---

## Common Scenarios

### Scenario 1: Experimental work

```bash
# Disable autocommit
export AUTOCOMMIT_DISABLE=1

# Try risky changes
# ... make changes ...

# If you like them, commit manually
git add .
git commit -m "experiment: new approach"

# If you don't, discard
git reset --hard HEAD

# Re-enable
unset AUTOCOMMIT_DISABLE
```

### Scenario 2: Undo an autocommit

```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1
```

### Scenario 3: Review before commit

```bash
# Disable autocommit
export AUTOCOMMIT_DISABLE=1

# Make changes
# ... edit files ...

# Review
git diff

# Commit manually if good
git add .
git commit -m "your message"

# Or re-enable autocommit
unset AUTOCOMMIT_DISABLE
```

---

## Troubleshooting

### Autocommit not working?

**Check:**
```bash
# Is it enabled?
echo $AUTOCOMMIT_DISABLE  # Should be empty or "0"

# Is git configured?
git config user.name
git config user.email

# Check the log
tail -20 ~/.claude/autocommit.log
```

### Commits too frequent?

```bash
# Increase batch window
export AUTOCOMMIT_BATCH_WINDOW=60  # Wait 60 seconds
```

### Commit messages low quality?

**Likely cause:** Auggie MCP is unavailable.

**Check:**
```bash
grep "Auggie" ~/.claude/autocommit.log
```

**Fix:** Ensure Auggie MCP server is running.

---

## Installation

If autocommit is not installed:

### 1. Copy hook script

```bash
# Create hooks directory
mkdir -p .claude/hooks

# Copy hook script (from another project or create new)
cp /path/to/autocommit_post.py .claude/hooks/

# Make executable
chmod +x .claude/hooks/autocommit_post.py
```

### 2. Register hook

Edit `.claude/settings.json` and add:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/autocommit_post.py\""
          }
        ]
      }
    ]
  }
}
```

### 3. Test

```bash
echo "test" > test.txt
sleep 30
git log -1
```

---

## FAQ

### Q: Will this commit sensitive data?

**A:** No more than manual commits. Use `.gitignore` as usual.

### Q: What if I'm offline?

**A:** Commits still work (git is local). Auggie calls may fail, using fallback messages.

### Q: Can I customize commit messages?

**A:** Yes, edit the prompt in `.claude/hooks/autocommit_post.py`.

### Q: Does this work with branches?

**A:** Yes, commits go to your current branch.

### Q: What about merge conflicts?

**A:** Autocommit skips commits during conflicts. Resolve manually, then it resumes.

### Q: How do I uninstall?

**A:** Remove the PostToolUse section from `.claude/settings.json`.

---

## Documentation

- **Quick Start:** This file
- **Research Report:** `AUTOCOMMIT_RESEARCH_REPORT.md` (why this approach)
- **Implementation Guide:** `AUTOCOMMIT_IMPLEMENTATION.md` (how to build it)
- **User Guide:** `AUTOCOMMIT_USER_GUIDE.md` (how to use it)
- **Testing Guide:** `AUTOCOMMIT_TESTING_GUIDE.md` (how to test it)
- **Summary:** `AUTOCOMMIT_SUMMARY.md` (executive overview)

---

## Support

### Getting Help

1. **Check the log:** `tail -20 ~/.claude/autocommit.log`
2. **Read the docs:** See `AUTOCOMMIT_USER_GUIDE.md`
3. **File an issue:** Report bugs or request features

### Reporting Issues

Include:
- Log output: `tail -50 ~/.claude/autocommit.log`
- Git status: `git status`
- Environment: `echo $AUTOCOMMIT_DISABLE`

---

## Benefits

### Time Savings

- **Before:** 2-5 minutes per commit × 10 commits/day = **20-50 min/day**
- **After:** 0 minutes per commit × 30 commits/day = **0 min/day**
- **Savings:** **20-50 minutes per day** ✅

### Quality Improvements

- ✅ Consistent commit messages (AI-generated)
- ✅ Better commit granularity (more frequent)
- ✅ No forgotten commits (automatic)
- ✅ Follows repo style (learns from recent commits)

### Developer Experience

- ✅ Focus on coding (not git operations)
- ✅ No context switching (commits in background)
- ✅ Easy rollback (finer-grained history)
- ✅ Dogfooding (uses our own Auggie tool)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code Workflow                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  Write/Edit Tool │
                  │   Completes      │
                  └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  PostToolUse     │
                  │  Hook Triggers   │
                  └──────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  .claude/hooks/autocommit_post.py     │
        │                                       │
        │  1. Check AUTOCOMMIT_DISABLE         │
        │  2. Collect modified files           │
        │  3. Run git diff                     │
        │  4. Call Auggie MCP (AI)             │
        │  5. Stage files                      │
        │  6. Commit with AI message           │
        │  7. Log to ~/.claude/autocommit.log  │
        └───────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  Git Commit      │
                  │  Created         │
                  └──────────────────┘
```

---

## Status

**Version:** 1.0  
**Status:** ✅ Implemented and ready for testing  
**Last Updated:** 2025-10-11

**What's working:**
- ✅ Hook infrastructure
- ✅ Batching logic
- ✅ Git operations
- ✅ Error handling
- ✅ Logging
- ✅ Fallback messages

**What's pending:**
- ⚠️ Auggie MCP integration (placeholder implemented)

---

## Example Commit

```
feat: add automated commit system via PostToolUse hook

Implements background commit automation that frees Claude agent from
manual git operations. Uses Auggie MCP to analyze diffs and generate
high-quality conventional commit messages.

Features:
- PostToolUse hook triggers after file edits
- AI-powered message generation (GPT-5 via Auggie)
- Intelligent batching (30s window)
- Toggleable via AUTOCOMMIT_DISABLE=1

Benefits:
- Eliminates manual commit message writing
- Ensures consistent commit message quality
- Frees Claude to focus on coding

Co-Authored-By: Auggie (GPT-5) <noreply@augmentcode.com>
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## Credits

**Researched, designed, and implemented by:** Claude (Sonnet 4.5)  
**Date:** 2025-10-11

**Dogfooding:** Uses our own Auggie MCP tool for commit message generation

---

**Enjoy automated commits! 🚀**

Questions? See `AUTOCOMMIT_USER_GUIDE.md` or check the log: `tail -f ~/.claude/autocommit.log`

