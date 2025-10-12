# Automated Commit System - User Guide

**Version:** 1.0  
**Last Updated:** 2025-10-11

---

## What is Autocommit?

Autocommit is a background automation system that **automatically commits your code changes** as you work, freeing you from manual git operations.

### How It Works

```
You edit a file → Claude Code saves it → Hook triggers → AI analyzes changes → Git commit created
```

**No manual intervention required!**

---

## Features

✅ **Fully Automatic** - Commits happen in the background  
✅ **AI-Powered Messages** - High-quality conventional commit messages  
✅ **Intelligent Batching** - Groups related changes (30s window)  
✅ **Toggleable** - Easy to enable/disable  
✅ **Non-Blocking** - Doesn't interrupt your work  
✅ **Logged** - All commits tracked in `~/.claude/autocommit.log`

---

## Quick Start

### Enable Autocommit

Autocommit is **enabled by default** once installed. No configuration needed!

### Disable Autocommit

**Temporarily (current session):**
```bash
export AUTOCOMMIT_DISABLE=1
```

**Permanently:**
Add to your `~/.bashrc` or `~/.zshrc`:
```bash
export AUTOCOMMIT_DISABLE=1
```

### Re-enable Autocommit

```bash
unset AUTOCOMMIT_DISABLE
```

---

## How It Works

### 1. You Edit Files

Work normally in Claude Code. When you edit files using:
- Write tool
- Edit tool  
- MultiEdit tool

The autocommit hook automatically triggers.

### 2. Batching Window (30 seconds)

After your first edit, autocommit waits **30 seconds** to see if you make more changes.

**Why?** To group related changes into a single commit instead of creating dozens of tiny commits.

**Example:**
```
14:30:00 - Edit file1.py
14:30:15 - Edit file2.py  
14:30:25 - Edit file3.py
14:30:55 - COMMIT (all 3 files together)
```

### 3. AI Analyzes Changes

Autocommit:
1. Runs `git diff` to see what changed
2. Sends diff to Auggie (GPT-5 or Claude)
3. Auggie generates a conventional commit message
4. Follows the style of your recent commits

### 4. Commit Created

Files are staged and committed automatically with the AI-generated message.

**Example commit:**
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

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTOCOMMIT_DISABLE` | `0` | Set to `1` to disable |
| `AUTOCOMMIT_BATCH_WINDOW` | `30` | Seconds to wait before committing |
| `AUTOCOMMIT_MAX_DIFF_SIZE` | `10000` | Max diff size (characters) |
| `AUTOCOMMIT_LOG_LEVEL` | `INFO` | Logging level |

### Examples

**Disable for a specific task:**
```bash
export AUTOCOMMIT_DISABLE=1
# ... do risky work ...
unset AUTOCOMMIT_DISABLE
```

**Increase batch window (wait longer):**
```bash
export AUTOCOMMIT_BATCH_WINDOW=60  # Wait 60 seconds
```

**Enable debug logging:**
```bash
export AUTOCOMMIT_LOG_LEVEL=DEBUG
tail -f ~/.claude/autocommit.log
```

---

## Monitoring

### View Autocommit Log

```bash
# View recent activity
tail -20 ~/.claude/autocommit.log

# Watch in real-time
tail -f ~/.claude/autocommit.log

# Search for errors
grep ERROR ~/.claude/autocommit.log
```

**Log format:**
```
2025-10-11 14:32:15 | INFO    | abc123f | feat: add new feature | 3 files
2025-10-11 14:35:42 | INFO    | SKIP | Empty diff | 0 files
2025-10-11 14:38:19 | ERROR   | ERROR | Auggie MCP timeout | 2 files
```

### View Recent Commits

```bash
# Last 10 commits
git log --oneline -10

# Commits from today
git log --since="today" --format="%h %s"

# Commits with stats
git log --since="1 day ago" --stat
```

---

## Common Scenarios

### Scenario 1: Rapid Development

**Situation:** You're making many small changes quickly.

**What happens:**
- First edit at 14:00:00
- More edits at 14:00:10, 14:00:20, 14:00:25
- Autocommit waits until 14:00:30 (30s after last edit)
- Creates single commit with all changes

**Result:** Clean commit history, not spammed with tiny commits.

---

### Scenario 2: Experimental Work

**Situation:** You're trying something risky and might want to discard changes.

**What to do:**
```bash
# Disable autocommit
export AUTOCOMMIT_DISABLE=1

# Do experimental work
# ... make changes ...

# If you like the changes, commit manually
git add .
git commit -m "experiment: trying new approach"

# If you don't like them, discard
git reset --hard HEAD

# Re-enable autocommit
unset AUTOCOMMIT_DISABLE
```

---

### Scenario 3: Large Refactoring

**Situation:** You're refactoring many files and want logical commit boundaries.

**Option A: Let autocommit handle it**
- Autocommit will batch changes every 30s
- You'll get commits like "refactor: update module structure (15 files)"

**Option B: Manual control**
```bash
# Disable autocommit
export AUTOCOMMIT_DISABLE=1

# Refactor step 1
# ... make changes ...
git add src/module1/
git commit -m "refactor: extract module1 logic"

# Refactor step 2
# ... make changes ...
git add src/module2/
git commit -m "refactor: simplify module2 interface"

# Re-enable autocommit
unset AUTOCOMMIT_DISABLE
```

---

### Scenario 4: Reviewing Changes Before Commit

**Situation:** You want to review changes before they're committed.

**What to do:**
```bash
# Disable autocommit
export AUTOCOMMIT_DISABLE=1

# Make changes
# ... edit files ...

# Review changes
git diff

# If good, commit manually
git add .
git commit -m "your message"

# Or re-enable autocommit and let it handle next changes
unset AUTOCOMMIT_DISABLE
```

---

## Troubleshooting

### Autocommit Not Working

**Symptoms:** Files are edited but no commits are created.

**Check:**
1. Is autocommit enabled?
   ```bash
   echo $AUTOCOMMIT_DISABLE
   # Should be empty or "0"
   ```

2. Is the hook installed?
   ```bash
   ls -l .claude/hooks/autocommit_post.py
   # Should exist and be executable
   ```

3. Check the log:
   ```bash
   tail -20 ~/.claude/autocommit.log
   # Look for errors
   ```

4. Is git configured?
   ```bash
   git config user.name
   git config user.email
   # Both should be set
   ```

---

### Commits Are Too Frequent

**Symptoms:** Getting a commit for every tiny change.

**Solution:** Increase batch window:
```bash
export AUTOCOMMIT_BATCH_WINDOW=60  # Wait 60 seconds
```

Or disable autocommit and commit manually when ready.

---

### Commit Messages Are Low Quality

**Symptoms:** Messages are generic like "chore: update 3 files".

**Likely cause:** Auggie MCP is unavailable or timing out.

**Check:**
```bash
# Look for "Auggie MCP unavailable" in log
grep "Auggie" ~/.claude/autocommit.log

# Test Auggie directly
auggie --model gpt5 "test prompt"
```

**Solution:**
1. Ensure Auggie MCP server is running
2. Check network connectivity
3. Increase timeout if needed

---

### Want to Undo an Autocommit

**Situation:** Autocommit created a commit you don't want.

**Solution:**
```bash
# Undo last commit (keeps changes)
git reset --soft HEAD~1

# Undo last commit (discards changes)
git reset --hard HEAD~1

# Undo and edit
git reset --soft HEAD~1
# ... make changes ...
git add .
git commit -m "better message"
```

**Note:** Autocommit uses Claude Code's checkpointing system, so you can also use `/checkpoint restore` to rollback.

---

## Best Practices

### ✅ DO

- **Let autocommit handle routine work** - It's designed for this
- **Disable for risky experiments** - Use `AUTOCOMMIT_DISABLE=1`
- **Review the log occasionally** - Catch any issues early
- **Trust the AI** - Auggie generates good messages 90%+ of the time
- **Use checkpointing** - Claude Code's built-in rollback system

### ❌ DON'T

- **Don't disable permanently** - You lose the benefits
- **Don't manually commit every time** - Defeats the purpose
- **Don't worry about perfect messages** - Good enough is fine
- **Don't commit sensitive data** - Use `.gitignore` as always

---

## FAQ

### Q: Will autocommit commit sensitive data?

**A:** No more than manual commits. Use `.gitignore` to exclude sensitive files as you normally would.

### Q: What if I'm offline?

**A:** Commits still work (git is local). Auggie MCP calls may fail, triggering fallback messages.

### Q: Can I customize commit message format?

**A:** Yes, edit the prompt in `.claude/hooks/autocommit_post.py` (see Implementation Guide).

### Q: Does this work with branches?

**A:** Yes, commits go to your current branch (whatever `git status` shows).

### Q: What about merge conflicts?

**A:** Autocommit skips commits if merge conflicts are detected. Resolve manually, then autocommit resumes.

### Q: Can I use this with GitHub/GitLab?

**A:** Yes! Autocommit just creates local commits. Push to remote as usual:
```bash
git push origin main
```

### Q: Does this replace manual commits?

**A:** For routine work, yes. For important milestones or releases, you may still want manual commits with detailed messages.

### Q: How do I uninstall?

**A:** Remove the PostToolUse hook from `.claude/settings.json`:
```bash
# Edit settings
vim .claude/settings.json

# Remove the PostToolUse section
# Save and exit
```

---

## Advanced Usage

### Custom Commit Message Templates

Edit `.claude/hooks/autocommit_post.py` and modify the `build_commit_prompt()` function to customize the prompt sent to Auggie.

### Integration with CI/CD

Autocommit works seamlessly with CI/CD:
```bash
# In CI pipeline
git push origin main
# Triggers CI/CD as normal
```

### Multiple Repositories

Autocommit is **project-specific** (configured in `.claude/settings.json`).

To use across all projects:
1. Copy hook to `~/.claude/hooks/`
2. Add to `~/.claude/settings.json` (global)

---

## Support

### Getting Help

1. **Check the log:** `tail -20 ~/.claude/autocommit.log`
2. **Read the docs:** See `AUTOCOMMIT_IMPLEMENTATION.md` for technical details
3. **File an issue:** Report bugs or request features

### Reporting Issues

Include:
- Log output: `tail -50 ~/.claude/autocommit.log`
- Git status: `git status`
- Environment: `echo $AUTOCOMMIT_DISABLE`
- Hook config: `cat .claude/settings.json | grep -A 10 PostToolUse`

---

## Changelog

### v1.0 (2025-10-11)
- Initial release
- PostToolUse hook implementation
- Auggie MCP integration
- 30s batching window
- Comprehensive logging

---

**Enjoy automated commits! 🚀**

Questions? Check the Implementation Guide or file an issue.

