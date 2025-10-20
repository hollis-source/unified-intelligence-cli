#!/usr/bin/env python3
"""Test PR Validation functionality (Phase 8B).

Tests the complete PR validation flow:
1. Test validator (runs pytest)
2. Coverage validator (checks coverage)
3. Conflict validator (checks merge conflicts)

Uses current branch as test PR.
"""

import subprocess
from src.claude_orchestrator.entities.pull_request import PullRequest, PRStatus
from src.claude_orchestrator.adapters.test_pr_validator import TestPRValidator
from src.claude_orchestrator.adapters.coverage_pr_validator import CoveragePRValidator
from src.claude_orchestrator.adapters.conflict_pr_validator import ConflictPRValidator
from src.claude_orchestrator.use_cases.validate_pr_use_case import ValidatePRUseCase

print("="*70)
print("PHASE 8B: PR VALIDATION TEST")
print("="*70)
print()

# Test 1: Get current branch
print("TEST 1: Analyze current branch")
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
print()

# Test 2: Create mock PullRequest
print("TEST 2: Create mock PullRequest")
print("-"*70)

pr = PullRequest.create(
    number=999,
    title=f"Test PR: {current_branch}",
    branch=current_branch,
    base_branch="priority/prod-010-clean",  # Use parent branch as base
    description="Test PR for validation",
    files_changed=files_changed if files_changed else ["test_review_sample.py"],
    status=PRStatus.OPEN,
)

print(f"✓ PR #{pr.number}: {pr.title}")
print(f"✓ Branch: {pr.branch} → {pr.base_branch}")
print()

# Test 3: Initialize Validators
print("TEST 3: Initialize validators")
print("-"*70)

test_validator = TestPRValidator(
    timeout_seconds=120,
    test_path="tests/",
)
print("✓ TestPRValidator initialized")

coverage_validator = CoveragePRValidator(
    min_coverage_percentage=70.0,  # Lenient for testing
    timeout_seconds=120,
)
print("✓ CoveragePRValidator initialized (threshold: 70%)")

conflict_validator = ConflictPRValidator(
    timeout_seconds=60,
)
print("✓ ConflictPRValidator initialized")
print()

# Test 4: Create Use Case
print("TEST 4: Create ValidatePRUseCase")
print("-"*70)

use_case = ValidatePRUseCase(
    validators=[
        conflict_validator,  # Fast, run first
        test_validator,      # Run tests
        coverage_validator,  # Check coverage
    ],
)

print("✓ Use case initialized with 3 validators (full validation)")
print()

# Test 5: Run Validation
print("TEST 5: Run PR validation")
print("-"*70)
print()

try:
    result = use_case.execute(
        pr=pr,
        project_path=".",
        fail_fast=True,
    )

    print()
    print("="*70)
    print("VALIDATION RESULTS")
    print("="*70)
    print(f"Overall Status: {result.overall_status.value}")
    print(f"Total Checks: {result.total_checks}")
    print(f"Passed: {result.passed_checks}")
    print(f"Failed: {result.failed_checks}")
    print(f"Skipped: {result.skipped_checks}")
    print(f"Total Time: {result.total_time_seconds:.1f}s")
    print()

    print("Check Results:")
    for check in result.checks:
        status_icon = "✅" if check.passed() else "❌"
        print(f"  {status_icon} {check.check_type.value}: {check.message}")
        if check.details:
            for key, value in list(check.details.items())[:3]:
                print(f"     - {key}: {value}")
    print()

    print("="*70)
    print("TEST RESULT")
    print("="*70)

    if result.is_valid():
        print("✅ PR VALIDATION PASSED - Ready to merge!")
    else:
        failed_checks = result.get_failed_checks()
        print(f"⚠️  PR HAS ISSUES - {len(failed_checks)} check(s) failed:")
        for check in failed_checks:
            print(f"   - {check.check_type.value}: {check.message}")

    print()
    print("🎉 Phase 8B validation system works!")
    print()
    print("To test full validation (tests + coverage), uncomment validators in script")

except Exception as e:
    print()
    print("="*70)
    print("TEST FAILED")
    print("="*70)
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print()
print("Done.")
