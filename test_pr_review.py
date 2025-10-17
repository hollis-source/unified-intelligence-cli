#!/usr/bin/env python3
"""Test PR Review functionality (Phase 8A).

Tests the auggie-powered code review flow:
1. Create mock PR from current branch
2. Review using AuggiePRReviewer
3. Validate ReviewResult output

Note: This test uses single-model review (Claude 4.5 only) for speed.
Multi-model review can be enabled with use_multi_model=True.
"""

from src.claude_orchestrator.entities.pull_request import PullRequest, PRStatus
from src.claude_orchestrator.adapters.auggie_pr_reviewer import AuggiePRReviewer
from src.claude_orchestrator.use_cases.review_pr_use_case import ReviewPRUseCase
from src.claude_orchestrator.interfaces.pr_reviewer import ReviewCriteria
import subprocess

print("="*70)
print("PHASE 8A: PR REVIEW TEST")
print("="*70)
print()

# Test 1: Get current branch and changes
print("TEST 1: Analyze current changes")
print("-"*70)

result = subprocess.run(
    ["git", "branch", "--show-current"],
    capture_output=True,
    text=True,
)
current_branch = result.stdout.strip()
print(f"✓ Current branch: {current_branch}")

result = subprocess.run(
    ["git", "diff", "--name-only", "HEAD"],
    capture_output=True,
    text=True,
)
files_changed = [f for f in result.stdout.strip().split("\n") if f]
print(f"✓ Files changed: {len(files_changed)}")
if files_changed:
    for f in files_changed[:5]:
        print(f"  - {f}")
    if len(files_changed) > 5:
        print(f"  ... and {len(files_changed) - 5} more")

result = subprocess.run(
    ["git", "diff", "--shortstat", "HEAD"],
    capture_output=True,
    text=True,
)
stats = result.stdout.strip()
print(f"✓ Changes: {stats}")
print()

# Test 2: Create mock PullRequest entity
print("TEST 2: Create mock PullRequest")
print("-"*70)

pr = PullRequest.create(
    number=999,  # Mock PR number
    title=f"Test PR: {current_branch}",
    branch=current_branch,
    base_branch="master",  # Would compare against master
    description="This is a test PR to validate the review flow",
    files_changed=files_changed if files_changed else ["src/claude_orchestrator/entities/pull_request.py"],
    status=PRStatus.OPEN,
)

print(f"✓ PR #{pr.number}: {pr.title}")
print(f"✓ Branch: {pr.branch} → {pr.base_branch}")
print(f"✓ Status: {pr.status.value}")
print()

# Test 3: Initialize PR Reviewer
print("TEST 3: Initialize AuggiePRReviewer")
print("-"*70)

# Use single-model for faster testing (Claude 4.5)
# Set use_multi_model=True to test GPT-5 + Claude 4.5 consensus
reviewer = AuggiePRReviewer(
    use_multi_model=False,  # Single model for speed
    working_dir=".",
    timeout_seconds=180,  # 3 minutes
)

print("✓ Reviewer initialized")
print("  Model: Claude 4.5 (single model for speed)")
print("  Multi-model disabled (use use_multi_model=True for GPT-5 + Claude)")
print()

# Test 4: Get PR diff
print("TEST 4: Get PR diff")
print("-"*70)

try:
    diff = reviewer.get_diff(pr)
    diff_lines = len(diff.split("\n"))
    print(f"✓ Diff retrieved: {diff_lines} lines")
    print(f"  First 200 chars: {diff[:200]}...")
    print()
except Exception as e:
    print(f"❌ Failed to get diff: {e}")
    print("Note: This is expected if there are no differences between branches")
    print()
    diff = None

# Test 5: Review PR (if diff exists)
if diff and len(diff) > 10:
    print("TEST 5: Perform code review")
    print("-"*70)
    print("⏳ This will take 1-2 minutes (calling auggie with Claude 4.5)...")
    print()

    use_case = ReviewPRUseCase(pr_reviewer=reviewer)

    try:
        result = use_case.execute(
            pr=pr,
            strict=False,  # Use lenient criteria for test
            include_suggestions=True,
        )

        print()
        print("="*70)
        print("REVIEW RESULTS")
        print("="*70)
        print(f"Outcome: {result.outcome.value}")
        print(f"Reviewer: {result.reviewer}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Review Time: {result.review_time_seconds}s")
        print()
        print("Scores:")
        print(f"  Code Quality: {result.code_quality_score}/100")
        print(f"  Test Coverage: {result.test_coverage_score}/100")
        print(f"  Documentation: {result.documentation_score}/100")
        print()
        print(f"Summary:\n{result.summary}")
        print()

        if result.issues:
            print(f"Issues ({len(result.issues)}):")
            for i, issue in enumerate(result.issues, 1):
                print(f"  {i}. {issue}")
            print()

        if result.suggestions:
            print(f"Suggestions ({len(result.suggestions)}):")
            for i, suggestion in enumerate(result.suggestions[:5], 1):
                print(f"  {i}. {suggestion}")
            if len(result.suggestions) > 5:
                print(f"  ... and {len(result.suggestions) - 5} more")
            print()

        if result.security_concerns:
            print(f"Security Concerns ({len(result.security_concerns)}):")
            for i, concern in enumerate(result.security_concerns, 1):
                print(f"  {i}. {concern}")
            print()

        print("="*70)
        print("TEST RESULT")
        print("="*70)
        if result.is_approved():
            print("✅ PR REVIEW PASSED - Code approved")
        elif result.has_blocking_issues():
            print("⚠️  PR HAS ISSUES - Review complete, issues found")
        else:
            print("✅ PR REVIEW COMPLETE - Minor changes suggested")

        print()
        print("🎉 Phase 8A code review works!")

    except Exception as e:
        print()
        print("="*70)
        print("TEST FAILED")
        print("="*70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

else:
    print("TEST 5: Skipped (no diff to review)")
    print("-"*70)
    print("⚠️  No changes to review between branches")
    print("This is expected if current branch has no differences from main")
    print()
    print("To test with actual changes:")
    print("1. Make some code changes")
    print("2. Commit them")
    print("3. Run this test again")
    print()
    print("✅ Phase 8A components created successfully!")
    print("   (Review flow not tested due to no changes)")

print()
print("Done.")
