# Automated Commit System - Testing Guide

**Version:** 1.0  
**Last Updated:** 2025-10-11

---

## Overview

This guide provides comprehensive testing procedures for the automated commit system.

**Test Coverage:**
- ✅ Basic functionality
- ✅ Batching logic
- ✅ Auggie MCP integration
- ✅ Error handling
- ✅ Edge cases
- ✅ Performance
- ✅ Rollback procedures

---

## Prerequisites

Before testing:
```bash
# Ensure git is configured
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Ensure hook is installed
ls -l .claude/hooks/autocommit_post.py

# Ensure hook is registered
cat .claude/settings.json | grep -A 5 PostToolUse

# Clear previous test commits (optional)
git reset --hard HEAD~10  # Careful!
```

---

## Test Suite

### Test 1: Basic Single File Commit

**Objective:** Verify autocommit works for a single file edit.

**Steps:**
```bash
# 1. Create test file
echo "test content" > test_autocommit_1.txt

# 2. Wait 30 seconds (batch window)
sleep 30

# 3. Verify commit was created
git log -1 --format="%s"
# Expected: "chore: update test_autocommit_1.txt" or similar

# 4. Check log
tail -5 ~/.claude/autocommit.log
# Expected: INFO line with commit hash
```

**Success Criteria:**
- ✅ Commit created within 30 seconds
- ✅ Commit message follows conventional format
- ✅ File is staged and committed
- ✅ Log entry created

---

### Test 2: Batching Multiple Files

**Objective:** Verify batching groups related changes.

**Steps:**
```bash
# 1. Create multiple files quickly
echo "file 1" > test_batch_1.txt
sleep 5
echo "file 2" > test_batch_2.txt
sleep 5
echo "file 3" > test_batch_3.txt

# 2. Wait for batch window (30s from last edit)
sleep 30

# 3. Verify single commit with all 3 files
git log -1 --stat
# Expected: Shows all 3 files in one commit

# 4. Check commit message
git log -1 --format="%s%n%b"
# Expected: Mentions "3 files" or lists all files
```

**Success Criteria:**
- ✅ Single commit created (not 3 separate commits)
- ✅ All 3 files included in commit
- ✅ Commit message mentions multiple files

---

### Test 3: Disable Toggle

**Objective:** Verify AUTOCOMMIT_DISABLE works.

**Steps:**
```bash
# 1. Disable autocommit
export AUTOCOMMIT_DISABLE=1

# 2. Create test file
echo "should not commit" > test_disabled.txt

# 3. Wait 30 seconds
sleep 30

# 4. Verify NO commit was created
git status
# Expected: test_disabled.txt is untracked

# 5. Re-enable
unset AUTOCOMMIT_DISABLE

# 6. Create another file
echo "should commit" > test_enabled.txt

# 7. Wait 30 seconds
sleep 30

# 8. Verify commit WAS created
git log -1 --format="%s"
# Expected: Commit for test_enabled.txt
```

**Success Criteria:**
- ✅ No commit when disabled
- ✅ Commit resumes when re-enabled
- ✅ Log shows skip when disabled

---

### Test 4: Empty Diff Handling

**Objective:** Verify autocommit skips empty diffs.

**Steps:**
```bash
# 1. Create and commit file manually
echo "content" > test_empty.txt
git add test_empty.txt
git commit -m "manual commit"

# 2. Touch file (no actual changes)
touch test_empty.txt

# 3. Wait 30 seconds
sleep 30

# 4. Verify NO new commit
git log -1 --format="%s"
# Expected: Still shows "manual commit"

# 5. Check log
grep "Empty diff" ~/.claude/autocommit.log
# Expected: Log entry about skipping empty diff
```

**Success Criteria:**
- ✅ No commit for empty diff
- ✅ Log shows "Empty diff, skipping commit"

---

### Test 5: Large Diff Handling

**Objective:** Verify large diffs are truncated but still committed.

**Steps:**
```bash
# 1. Create large file (>10KB)
python3 -c "print('x' * 15000)" > test_large.txt

# 2. Wait 30 seconds
sleep 30

# 3. Verify commit was created
git log -1 --format="%s"
# Expected: Commit created

# 4. Check log for truncation warning
grep "truncated" ~/.claude/autocommit.log
# Expected: May show truncation message
```

**Success Criteria:**
- ✅ Commit created despite large diff
- ✅ No errors in log
- ✅ Commit message still meaningful

---

### Test 6: Auggie MCP Integration

**Objective:** Verify Auggie generates quality commit messages.

**Steps:**
```bash
# 1. Create meaningful change
cat > test_feature.py << 'EOF'
def calculate_sum(a, b):
    """Calculate sum of two numbers."""
    return a + b

def calculate_product(a, b):
    """Calculate product of two numbers."""
    return a * b
EOF

# 2. Wait 30 seconds
sleep 30

# 3. Check commit message quality
git log -1 --format="%s%n%b"
# Expected: Meaningful message like "feat: add math utility functions"

# 4. Verify Auggie was used (not fallback)
tail -10 ~/.claude/autocommit.log | grep -v "Auggie unavailable"
# Expected: No "unavailable" messages
```

**Success Criteria:**
- ✅ Commit message is descriptive (not generic)
- ✅ Follows conventional commit format
- ✅ Explains WHAT and WHY
- ✅ No "Auggie unavailable" in log

---

### Test 7: Fallback Message Generation

**Objective:** Verify fallback works when Auggie unavailable.

**Steps:**
```bash
# 1. Simulate Auggie failure (edit hook script temporarily)
# Comment out Auggie call in autocommit_post.py
# Or stop Auggie MCP server

# 2. Create test file
echo "test fallback" > test_fallback.txt

# 3. Wait 30 seconds
sleep 30

# 4. Check commit message
git log -1 --format="%s%n%b"
# Expected: Generic message like "chore: update test_fallback.txt"
# Body should mention "Auggie MCP unavailable"

# 5. Restore Auggie
# Uncomment Auggie call or restart server
```

**Success Criteria:**
- ✅ Commit still created (doesn't fail)
- ✅ Fallback message is reasonable
- ✅ Log shows Auggie failure

---

### Test 8: Multiple File Types

**Objective:** Verify correct categorization of different file types.

**Steps:**
```bash
# 1. Create documentation file
echo "# Documentation" > test_docs.md
sleep 30

# 2. Check commit type
git log -1 --format="%s"
# Expected: "docs: ..." prefix

# 3. Create test file
cat > test_unit.py << 'EOF'
def test_example():
    assert True
EOF
sleep 30

# 4. Check commit type
git log -1 --format="%s"
# Expected: "test: ..." prefix

# 5. Create source file
cat > test_source.py << 'EOF'
def new_feature():
    return "feature"
EOF
sleep 30

# 6. Check commit type
git log -1 --format="%s"
# Expected: "feat: ..." or "chore: ..." prefix
```

**Success Criteria:**
- ✅ Docs files get "docs:" prefix
- ✅ Test files get "test:" prefix
- ✅ Source files get appropriate prefix

---

### Test 9: Error Recovery

**Objective:** Verify graceful handling of git errors.

**Steps:**
```bash
# 1. Create merge conflict scenario
git checkout -b test-branch
echo "branch content" > conflict.txt
git add conflict.txt
git commit -m "branch commit"

git checkout main
echo "main content" > conflict.txt
git add conflict.txt
git commit -m "main commit"

git merge test-branch
# Expected: Merge conflict

# 2. Try to edit file (should skip autocommit)
echo "more content" >> conflict.txt
sleep 30

# 3. Check log
grep "conflict" ~/.claude/autocommit.log
# Expected: Skip message or error

# 4. Resolve conflict
git merge --abort
git branch -D test-branch
```

**Success Criteria:**
- ✅ No commit during merge conflict
- ✅ Error logged appropriately
- ✅ Hook doesn't crash

---

### Test 10: Performance Test

**Objective:** Verify hook doesn't slow down Claude Code.

**Steps:**
```bash
# 1. Time hook execution
time (echo '{"tool_input":{"file_path":"test.txt"}}' | python3 .claude/hooks/autocommit_post.py)
# Expected: < 1 second (excluding 30s batch wait)

# 2. Create many files rapidly
for i in {1..10}; do
    echo "file $i" > test_perf_$i.txt
    sleep 1
done

# 3. Wait for batch commit
sleep 30

# 4. Verify single commit with all files
git log -1 --stat | grep "test_perf" | wc -l
# Expected: 10 files

# 5. Check total time
# Expected: ~40 seconds total (10s creation + 30s batch)
```

**Success Criteria:**
- ✅ Hook executes quickly (< 1s)
- ✅ Batching works with many files
- ✅ No performance degradation

---

## Edge Case Tests

### Edge Case 1: Detached HEAD

```bash
# 1. Checkout specific commit (detached HEAD)
git checkout HEAD~1

# 2. Try to edit file
echo "detached" > test_detached.txt
sleep 30

# 3. Verify behavior
git status
# Expected: Should skip or warn

# 4. Return to branch
git checkout main
```

---

### Edge Case 2: No Git Repository

```bash
# 1. Create temp directory without git
mkdir /tmp/no-git-test
cd /tmp/no-git-test

# 2. Try to run hook
echo '{"tool_input":{"file_path":"test.txt"}}' | python3 ~/.claude/hooks/autocommit_post.py

# 3. Check log
tail -5 ~/.claude/autocommit.log
# Expected: Error about no git repo

# 4. Cleanup
cd -
rm -rf /tmp/no-git-test
```

---

### Edge Case 3: Permission Denied

```bash
# 1. Make .git directory read-only
chmod -R 444 .git

# 2. Try to commit
echo "test" > test_permission.txt
sleep 30

# 3. Check log
grep "Permission denied" ~/.claude/autocommit.log

# 4. Restore permissions
chmod -R 755 .git
```

---

## Rollback Testing

### Test Rollback Procedure

**Objective:** Verify commits can be undone.

**Steps:**
```bash
# 1. Create test commit
echo "rollback test" > test_rollback.txt
sleep 30

# 2. Note commit hash
COMMIT_HASH=$(git rev-parse HEAD)

# 3. Undo commit (keep changes)
git reset --soft HEAD~1

# 4. Verify file still exists but uncommitted
git status
# Expected: test_rollback.txt is staged

# 5. Redo commit
git commit -m "manual commit after rollback"

# 6. Or discard changes
git reset --hard HEAD~1
```

**Success Criteria:**
- ✅ Can undo commits easily
- ✅ Changes preserved or discarded as desired
- ✅ No data loss

---

## Integration Tests

### Test with Claude Code Checkpointing

```bash
# 1. Create checkpoint
# (Use Claude Code's /checkpoint create command)

# 2. Make changes (autocommit will trigger)
echo "checkpoint test" > test_checkpoint.txt
sleep 30

# 3. Verify commit
git log -1

# 4. Restore checkpoint
# (Use Claude Code's /checkpoint restore command)

# 5. Verify changes reverted
git log -1
# Expected: Back to checkpoint state
```

---

## Continuous Testing

### Automated Test Script

Create `test_autocommit.sh`:

```bash
#!/bin/bash
# Automated test suite for autocommit

set -e

echo "=== Autocommit Test Suite ==="

# Test 1: Basic commit
echo "Test 1: Basic commit"
echo "test" > test1.txt
sleep 30
git log -1 --format="%s" | grep -q "test1.txt" && echo "✅ PASS" || echo "❌ FAIL"

# Test 2: Batching
echo "Test 2: Batching"
echo "a" > test2a.txt
sleep 5
echo "b" > test2b.txt
sleep 30
git log -1 --stat | grep -q "test2a.txt" && grep -q "test2b.txt" && echo "✅ PASS" || echo "❌ FAIL"

# Test 3: Disable toggle
echo "Test 3: Disable toggle"
export AUTOCOMMIT_DISABLE=1
echo "disabled" > test3.txt
sleep 30
git status | grep -q "test3.txt" && echo "✅ PASS" || echo "❌ FAIL"
unset AUTOCOMMIT_DISABLE

# Cleanup
git reset --hard HEAD~3
rm -f test*.txt

echo "=== Tests Complete ==="
```

Run tests:
```bash
chmod +x test_autocommit.sh
./test_autocommit.sh
```

---

## Monitoring During Testing

### Real-time Monitoring

**Terminal 1: Watch log**
```bash
tail -f ~/.claude/autocommit.log
```

**Terminal 2: Watch git log**
```bash
watch -n 5 'git log --oneline -5'
```

**Terminal 3: Run tests**
```bash
# Run test commands here
```

---

## Test Checklist

Before declaring autocommit production-ready:

- [ ] Test 1: Basic single file commit ✅
- [ ] Test 2: Batching multiple files ✅
- [ ] Test 3: Disable toggle ✅
- [ ] Test 4: Empty diff handling ✅
- [ ] Test 5: Large diff handling ✅
- [ ] Test 6: Auggie MCP integration ✅
- [ ] Test 7: Fallback message generation ✅
- [ ] Test 8: Multiple file types ✅
- [ ] Test 9: Error recovery ✅
- [ ] Test 10: Performance test ✅
- [ ] Edge case: Detached HEAD ✅
- [ ] Edge case: No git repository ✅
- [ ] Edge case: Permission denied ✅
- [ ] Rollback procedure ✅
- [ ] Integration with checkpointing ✅

---

## Reporting Test Results

### Test Report Template

```markdown
# Autocommit Test Report

**Date:** YYYY-MM-DD
**Tester:** Your Name
**Environment:** OS, Claude Code version, Git version

## Test Results

| Test | Status | Notes |
|------|--------|-------|
| Basic commit | ✅ PASS | Commit created in 30s |
| Batching | ✅ PASS | 3 files in 1 commit |
| Disable toggle | ✅ PASS | No commit when disabled |
| Empty diff | ✅ PASS | Skipped correctly |
| Large diff | ✅ PASS | Truncated, committed |
| Auggie integration | ✅ PASS | Quality messages |
| Fallback | ✅ PASS | Generic message used |
| File types | ✅ PASS | Correct prefixes |
| Error recovery | ✅ PASS | Graceful handling |
| Performance | ✅ PASS | < 1s execution |

## Issues Found

1. None

## Recommendations

1. Deploy to production
2. Monitor for 1 week
3. Gather user feedback

## Sign-off

Tested by: _______________
Date: _______________
```

---

## Troubleshooting Test Failures

### If tests fail:

1. **Check log:** `tail -50 ~/.claude/autocommit.log`
2. **Verify hook:** `python3 .claude/hooks/autocommit_post.py < /dev/null`
3. **Check git:** `git status && git config -l`
4. **Test Auggie:** `auggie --model gpt5 "test"`
5. **Review settings:** `cat .claude/settings.json`

### Common issues:

- **Hook not executable:** `chmod +x .claude/hooks/autocommit_post.py`
- **Python errors:** Check Python version (need 3.8+)
- **Git errors:** Ensure git is configured
- **Auggie errors:** Ensure MCP server is running

---

## Next Steps After Testing

1. ✅ All tests pass → Deploy to production
2. ⚠️ Some tests fail → Debug and retest
3. ❌ Many tests fail → Review implementation

---

**Testing by:** Claude (Sonnet 4.5)  
**Date:** 2025-10-11  
**Status:** ✅ Ready for testing

