# Automated Commit System - Research & Design Report

**Date:** 2025-10-11  
**Author:** Claude (Sonnet 4.5)  
**Status:** Ready for Implementation

---

## Executive Summary

**RECOMMENDATION:** Implement PostToolUse hook with AI-powered commit message generation via Auggie MCP.

**Key Benefits:**
- ✅ Zero manual intervention (fully automated)
- ✅ High-quality commit messages (AI analyzes diffs)
- ✅ Toggleable (AUTOCOMMIT_DISABLE=1)
- ✅ Dogfooding (uses our own Auggie MCP tool)
- ✅ Batches related changes intelligently
- ✅ Non-blocking (doesn't interrupt work)

**Implementation Time:** ~2-3 hours  
**Complexity:** Medium (hook + MCP integration)

---

## 1. EVALUATION OF AUTOMATION OPTIONS

### A. Claude Code PostToolUse Hook ⭐ **RECOMMENDED**

**How it works:**
- Triggers after Write, Edit, MultiEdit tools complete
- Analyzes git diff of changed files
- Calls Auggie MCP to generate commit message
- Stages and commits files automatically

**Pros:**
- ✅ Native Claude Code integration (no external processes)
- ✅ Runs automatically after every file edit
- ✅ Access to tool metadata (file paths, descriptions)
- ✅ Can batch multiple edits before committing
- ✅ Non-blocking (execution continues regardless)
- ✅ Easy to toggle on/off (env var)
- ✅ Survives context switches (persisted in settings)

**Cons:**
- ⚠️ Requires hook script maintenance
- ⚠️ Depends on Auggie MCP availability
- ⚠️ May create many small commits (mitigated by batching)

**Verdict:** **BEST OPTION** - Native, reliable, dogfoods our tools

---

### B. Git Hooks (post-commit, pre-commit)

**How it works:**
- Native git hooks trigger on git operations
- Would need to detect file changes and auto-stage

**Pros:**
- ✅ Standard git mechanism
- ✅ Works outside Claude Code

**Cons:**
- ❌ Doesn't know WHEN Claude edits files (only after manual git commands)
- ❌ Can't access Claude's tool metadata
- ❌ Requires manual `git add` first (defeats automation purpose)
- ❌ Harder to integrate with AI for message generation

**Verdict:** **NOT SUITABLE** - Doesn't solve the core problem

---

### C. Background Watcher Process (inotify/fswatch)

**How it works:**
- Daemon watches filesystem for changes
- Auto-commits when files modified

**Pros:**
- ✅ Works independently of Claude Code
- ✅ Can batch changes over time window

**Cons:**
- ❌ Requires separate daemon process
- ❌ No context about WHY files changed
- ❌ Can't distinguish Claude edits from other changes
- ❌ Complex setup and maintenance
- ❌ Resource overhead (constant filesystem monitoring)

**Verdict:** **OVERKILL** - Too complex for the problem

---

### D. MCP Server for Git Operations

**How it works:**
- Wrap git commands in MCP server
- Claude calls MCP instead of direct git

**Pros:**
- ✅ Centralized git logic
- ✅ Could batch operations

**Cons:**
- ❌ Requires Claude to CHOOSE to use it (not automatic)
- ❌ Doesn't solve "freeing Claude from manual work" problem
- ❌ Still requires Claude to craft messages
- ❌ Significant development effort

**Verdict:** **DOESN'T SOLVE PROBLEM** - Still manual

---

### E. Slash Command + Automatic Execution

**How it works:**
- Create `/autocommit` slash command
- Hook automatically triggers it after edits

**Pros:**
- ✅ User-visible control
- ✅ Can be manually invoked

**Cons:**
- ❌ Redundant with PostToolUse hook (same mechanism)
- ❌ Extra complexity for no benefit
- ❌ Slash commands are for user interaction, not automation

**Verdict:** **REDUNDANT** - PostToolUse hook is cleaner

---

### F. SessionEnd Hook

**How it works:**
- Commits everything at end of session
- Batched approach

**Pros:**
- ✅ Single commit per session
- ✅ Simple implementation

**Cons:**
- ❌ Loses granularity (all changes in one commit)
- ❌ If session crashes, changes lost
- ❌ Can't review/rollback individual changes
- ❌ Commit message quality suffers (too much in one commit)

**Verdict:** **TOO COARSE** - Loses valuable commit history

---

## 2. RECOMMENDED ARCHITECTURE

### **Option A: PostToolUse Hook with Auggie MCP** ⭐

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
        │  1. Check AUTOCOMMIT_DISABLE env var │
        │  2. Collect modified files           │
        │  3. Run git diff for context         │
        │  4. Call Auggie MCP to generate msg  │
        │  5. Stage files (git add)            │
        │  6. Commit with generated message    │
        │  7. Log commit hash                  │
        └───────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  Auggie MCP      │
                  │  (GPT-5/Claude)  │
                  │                  │
                  │  Analyzes diff   │
                  │  Generates msg   │
                  └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  Git Commit      │
                  │  Created         │
                  └──────────────────┘
```

### Key Components

1. **Hook Script:** `.claude/hooks/autocommit_post.py`
   - Python script (like ultrathink_submit.py)
   - Receives PostToolUse event JSON via stdin
   - Extracts file paths from tool_input
   - Runs git diff to get changes
   - Calls Auggie MCP for message generation
   - Executes git add + git commit

2. **Hook Configuration:** `.claude/settings.json`
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

3. **Auggie MCP Integration:**
   - Use existing `auggie_with_gpt5` or `auggie_with_claude` MCP tools
   - Pass git diff as context
   - Request commit message in conventional format
   - Parse response and extract message

4. **Batching Logic:**
   - Track last commit timestamp in temp file
   - If < 30 seconds since last commit, accumulate changes
   - After 30 seconds of inactivity, commit batch
   - Prevents commit spam during rapid edits

---

## 3. DESIGN REQUIREMENTS

### MUST HAVE ✅

- [x] Run automatically without Claude agent intervention
- [x] Generate high-quality commit messages (analyze git diff)
- [x] Be toggleable (AUTOCOMMIT_DISABLE=1 env var)
- [x] Handle multiple files in single commit intelligently
- [x] Follow conventional commit format (feat:, fix:, docs:, etc.)
- [x] Work across context switches (persisted in settings)
- [x] Not interrupt active work (non-blocking)
- [x] Be reliable (don't lose changes)

### SHOULD HAVE 🎯

- [x] Batch related changes when sensible (30s window)
- [x] Use AI (GPT-5 or Claude) to analyze diffs and generate messages
- [x] Support manual override when needed (disable via env var)
- [x] Log what it commits for visibility (~/.claude/autocommit.log)
- [x] Handle edge cases (merge conflicts, empty diffs, large diffs)

### NICE TO HAVE 💡

- [ ] Notify user of commits (optional notification hook)
- [ ] Allow custom commit message templates
- [ ] Support different batching strategies (time-based, file-count-based)
- [ ] Integration with PR/issue tracking (auto-link commits)

---

## 4. COMMIT MESSAGE QUALITY STRATEGY

### Analysis Approach

**Input to Auggie:**
```
Analyze this git diff and generate a conventional commit message.

DIFF:
<git diff output>

REQUIREMENTS:
- Use conventional commit format: <type>: <subject>
- Types: feat, fix, docs, refactor, test, chore, style, perf
- Subject: imperative mood, lowercase, no period, <50 chars
- Body: explain WHAT and WHY (not HOW), wrap at 72 chars
- Include benefits/impact if significant
- Match style of recent commits in this repo

RECENT COMMITS (for style reference):
<last 3 commit messages>

Generate ONLY the commit message, no explanation.
```

**Output Format:**
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
- Logs all commits to ~/.claude/autocommit.log

Benefits:
- Eliminates 30-50 lines of manual commit message writing
- Frees Claude to focus on coding, not git operations
- Ensures consistent commit message quality
- Dogfoods our own Auggie MCP tool

Co-Authored-By: Auggie (GPT-5) <noreply@augmentcode.com>
```

### Categorization Logic

```python
def categorize_commit(diff_content: str, file_paths: list) -> str:
    """Determine commit type from diff analysis."""
    
    # Check file extensions
    if any(f.endswith('.md') or f.endswith('.txt') for f in file_paths):
        if all(f.endswith(('.md', '.txt')) for f in file_paths):
            return 'docs'
    
    if any(f.startswith('test_') or '/tests/' in f for f in file_paths):
        return 'test'
    
    # Analyze diff content
    if 'def test_' in diff_content or 'class Test' in diff_content:
        return 'test'
    
    if 'TODO' in diff_content or 'FIXME' in diff_content:
        return 'chore'
    
    # Default to feat for new functionality, fix for bug fixes
    # Let Auggie decide based on diff analysis
    return None  # Auggie will determine
```

---

## 5. BATCHING LOGIC

### Time-Based Batching (Recommended)

**Strategy:** Wait 30 seconds after last edit before committing

**Implementation:**
```python
import time
import os

BATCH_WINDOW = 30  # seconds
TIMESTAMP_FILE = "/tmp/claude_autocommit_last_edit"

def should_commit_now():
    """Check if enough time has passed since last edit."""
    if not os.path.exists(TIMESTAMP_FILE):
        return True
    
    last_edit = float(open(TIMESTAMP_FILE).read())
    elapsed = time.time() - last_edit
    
    return elapsed >= BATCH_WINDOW

def update_timestamp():
    """Record current time as last edit."""
    with open(TIMESTAMP_FILE, 'w') as f:
        f.write(str(time.time()))
```

**Behavior:**
- Edit file A → timestamp updated, no commit
- Edit file B (10s later) → timestamp updated, no commit
- Edit file C (15s later) → timestamp updated, no commit
- Wait 30s → commit all 3 files together

**Benefits:**
- Reduces commit spam during rapid development
- Groups related changes logically
- Still commits frequently enough for safety

---

## 6. ERROR HANDLING

### Edge Cases & Mitigations

| Edge Case | Detection | Mitigation |
|-----------|-----------|------------|
| **Empty diff** | `git diff` returns empty | Skip commit, log warning |
| **Merge conflict** | `git status` shows conflict | Skip commit, notify user |
| **Large diff (>10KB)** | Check diff size | Truncate for Auggie, commit anyway |
| **Auggie MCP unavailable** | MCP call fails | Use fallback template message |
| **Git command fails** | Non-zero exit code | Log error, don't retry |
| **Permission denied** | Git error message | Log error, suggest fix |
| **Detached HEAD** | `git status` check | Skip commit, log warning |

### Fallback Commit Message

```python
def generate_fallback_message(file_paths: list) -> str:
    """Generate simple message when Auggie unavailable."""
    file_count = len(file_paths)
    
    if file_count == 1:
        return f"chore: update {os.path.basename(file_paths[0])}\n\nAutomatic commit (Auggie unavailable)"
    else:
        return f"chore: update {file_count} files\n\nAutomatic commit (Auggie unavailable)"
```

---

## 7. VISIBILITY & LOGGING

### Log File: `~/.claude/autocommit.log`

**Format:**
```
2025-10-11 14:32:15 | COMMIT | abc123f | feat: add autocommit system | 3 files
2025-10-11 14:35:42 | SKIP   | -       | Empty diff                  | 0 files
2025-10-11 14:38:19 | ERROR  | -       | Auggie MCP timeout          | 2 files
2025-10-11 14:40:55 | COMMIT | def456a | fix: handle edge cases      | 1 file
```

**Implementation:**
```python
import logging
from datetime import datetime

logging.basicConfig(
    filename=os.path.expanduser('~/.claude/autocommit.log'),
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-6s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_commit(commit_hash: str, message: str, file_count: int):
    """Log successful commit."""
    subject = message.split('\n')[0]
    logging.info(f"{commit_hash[:7]} | {subject} | {file_count} files")

def log_skip(reason: str):
    """Log skipped commit."""
    logging.info(f"SKIP | {reason}")

def log_error(error: str, file_count: int):
    """Log error."""
    logging.error(f"ERROR | {error} | {file_count} files")
```

---

## 8. TRADE-OFFS & LIMITATIONS

### Trade-offs

| Aspect | Trade-off | Mitigation |
|--------|-----------|------------|
| **Commit frequency** | Too many commits vs too few | 30s batching window |
| **Message quality** | AI-generated vs human-crafted | Use Auggie + recent commits as examples |
| **Performance** | Hook latency vs thoroughness | Run async, don't block Claude |
| **Reliability** | Auto-commit vs manual review | Checkpointing allows rollback |
| **Complexity** | Simple vs feature-rich | Start simple, iterate |

### Limitations

1. **Requires Auggie MCP:** If Auggie is down, falls back to template messages
2. **Network dependency:** MCP calls require network (local fallback available)
3. **Git-only:** Doesn't work with other VCS (Mercurial, SVN)
4. **Single branch:** Always commits to current branch (no auto-branching)
5. **No PR creation:** Just commits, doesn't create pull requests

### Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Bad commit messages** | Low | Medium | Auggie review + fallback templates |
| **Commit spam** | Medium | Low | 30s batching window |
| **Lost changes** | Very Low | High | Git history + checkpointing |
| **Hook script bugs** | Medium | Medium | Extensive testing + error handling |
| **Auggie unavailable** | Low | Low | Fallback message generation |

---

## 9. COMPARISON TO ALTERNATIVES

### Why PostToolUse Hook Beats Alternatives

| Criterion | PostToolUse Hook | Git Hooks | Watcher Daemon | MCP Server | SessionEnd |
|-----------|------------------|-----------|----------------|------------|------------|
| **Automatic** | ✅ Yes | ❌ No | ✅ Yes | ❌ No | ✅ Yes |
| **Context-aware** | ✅ Yes | ❌ No | ❌ No | ⚠️ Partial | ⚠️ Partial |
| **Non-blocking** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Easy setup** | ✅ Yes | ⚠️ Medium | ❌ No | ❌ No | ✅ Yes |
| **Maintenance** | ✅ Low | ✅ Low | ❌ High | ❌ High | ✅ Low |
| **Granularity** | ✅ High | ✅ High | ✅ High | ✅ High | ❌ Low |
| **Dogfooding** | ✅ Yes | ❌ No | ❌ No | ⚠️ Partial | ❌ No |

**Winner:** PostToolUse Hook (6/7 criteria)

---

## 10. NEXT STEPS

### Implementation Milestones

1. **Milestone 1: Basic Hook (1 hour)**
   - Create `.claude/hooks/autocommit_post.py`
   - Implement basic file detection and git diff
   - Add to `.claude/settings.json`
   - Test with simple file edits

2. **Milestone 2: Auggie Integration (1 hour)**
   - Integrate Auggie MCP for message generation
   - Implement fallback message logic
   - Test with various diff sizes and types

3. **Milestone 3: Batching & Polish (30 min)**
   - Add 30s batching window
   - Implement logging to ~/.claude/autocommit.log
   - Add error handling for edge cases

4. **Milestone 4: Testing & Documentation (30 min)**
   - Test all edge cases
   - Write user documentation
   - Create troubleshooting guide

**Total Time:** ~3 hours

---

## 11. SUCCESS METRICS

### How to Measure Success

1. **Time Saved:**
   - Before: ~2-5 min per commit (staging + message writing)
   - After: ~0 min (fully automated)
   - **Target:** 100% reduction in manual commit time

2. **Commit Quality:**
   - Measure: Compare AI-generated vs human-written messages
   - **Target:** 80%+ of commits require no manual editing

3. **Commit Frequency:**
   - Before: ~5-10 commits per day (manual)
   - After: ~20-30 commits per day (automated)
   - **Target:** 2-3x increase in commit frequency

4. **Reliability:**
   - Measure: % of successful auto-commits
   - **Target:** 95%+ success rate

5. **User Satisfaction:**
   - Measure: User feedback on commit message quality
   - **Target:** "Good enough" or better for 90%+ of commits

---

## 12. CONCLUSION

**RECOMMENDATION:** Implement PostToolUse hook with Auggie MCP integration.

**Why:**
- ✅ Solves the core problem (frees Claude from manual git work)
- ✅ High-quality commit messages (AI-powered)
- ✅ Dogfoods our own tools (Auggie MCP)
- ✅ Easy to implement (~3 hours)
- ✅ Easy to maintain (single Python script)
- ✅ Easy to toggle (env var)
- ✅ Non-blocking (doesn't interrupt work)

**Next Action:** Proceed to implementation (see AUTOCOMMIT_IMPLEMENTATION.md)

---

**Researched and designed by:** Claude (Sonnet 4.5)  
**Date:** 2025-10-11  
**Status:** ✅ Ready for Implementation

