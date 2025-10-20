"""Auggie PR Reviewer Adapter.

Uses auggie MCP for AI-powered code review with multi-model validation.

Clean Architecture: Adapter layer
SOLID: DIP - Implements IPRReviewer abstraction
"""

import subprocess
import tempfile
import os
import json
import re
from typing import Optional, Tuple
from datetime import datetime

from src.claude_orchestrator.interfaces.pr_reviewer import (
    IPRReviewer,
    ReviewCriteria,
    PRReviewError,
)
from src.claude_orchestrator.entities.pull_request import (
    PullRequest,
    ReviewResult,
    ReviewOutcome,
)


class AuggiePRReviewer(IPRReviewer):
    """
    PR Reviewer using auggie MCP with multi-model validation.

    Uses both GPT-5 and Claude 4.5 for comprehensive review:
    - GPT-5: Pragmatic, fast, catches practical issues
    - Claude 4.5: Rigorous, thorough, catches subtle issues

    Requires consensus for approval.
    """

    def __init__(
        self,
        use_multi_model: bool = True,
        working_dir: str = ".",
        timeout_seconds: int = 300,
    ):
        """
        Initialize Auggie PR Reviewer.

        Args:
            use_multi_model: Use both GPT-5 and Claude 4.5 (recommended)
            working_dir: Git repository working directory
            timeout_seconds: Timeout for auggie calls
        """
        self.use_multi_model = use_multi_model
        self.working_dir = working_dir
        self.timeout_seconds = timeout_seconds

    def review_pr(
        self,
        pr: PullRequest,
        criteria: Optional[ReviewCriteria] = None,
        include_suggestions: bool = True,
    ) -> ReviewResult:
        """
        Review PR using auggie (multi-model if enabled).

        Args:
            pr: Pull Request to review
            criteria: Review criteria
            include_suggestions: Include improvement suggestions

        Returns:
            ReviewResult with combined review from all models

        Raises:
            PRReviewError: If review fails
        """
        start_time = datetime.now()

        # Get PR diff
        try:
            diff = self.get_diff(pr)
        except Exception as e:
            raise PRReviewError(f"Failed to get PR diff: {e}")

        # Use default criteria if none provided
        criteria = criteria or ReviewCriteria()

        # Create review instruction
        instruction = self._create_review_instruction(pr, diff, criteria, include_suggestions)

        # Get reviews from models
        if self.use_multi_model:
            # Multi-model review (GPT-5 + Claude 4.5)
            review_gpt5 = self._review_with_model(instruction, "gpt5", "GPT-5")
            review_claude = self._review_with_model(instruction, "claude", "Claude 4.5")

            # Combine reviews
            result = self._combine_reviews(pr, [review_gpt5, review_claude], start_time)
        else:
            # Single model review (Claude 4.5 only)
            review = self._review_with_model(instruction, "claude", "Claude 4.5")
            result = review

        return result

    def get_diff(self, pr: PullRequest) -> str:
        """
        Get diff for PR using git.

        Args:
            pr: Pull Request

        Returns:
            Git diff as string

        Raises:
            PRReviewError: If git fails
        """
        try:
            # Try standard three-dot diff first
            cmd = [
                "git",
                "-C",
                self.working_dir,
                "diff",
                f"{pr.base_branch}...{pr.branch}",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # If three-dot fails (no merge base), try two-dot diff
            if result.returncode != 0:
                cmd = [
                    "git",
                    "-C",
                    self.working_dir,
                    "diff",
                    f"{pr.base_branch}..{pr.branch}",
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    # If both fail, try simple diff against HEAD~1
                    cmd = [
                        "git",
                        "-C",
                        self.working_dir,
                        "diff",
                        "HEAD~1",
                        pr.branch,
                    ]

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    if result.returncode != 0:
                        raise PRReviewError(f"Git diff failed: {result.stderr}")

            return result.stdout

        except subprocess.TimeoutExpired:
            raise PRReviewError("Git diff timed out")
        except Exception as e:
            raise PRReviewError(f"Failed to get diff: {e}")

    def _create_review_instruction(
        self,
        pr: PullRequest,
        diff: str,
        criteria: ReviewCriteria,
        include_suggestions: bool,
    ) -> str:
        """Create review instruction for auggie."""
        instruction = f"""You are an expert code reviewer. Review this Pull Request thoroughly.

# Pull Request Information
**Title:** {pr.title}
**Branch:** {pr.branch} → {pr.base_branch}
**Description:** {pr.description}
**Files Changed:** {len(pr.files_changed)} files
**Changes:** +{pr.additions} -{pr.deletions}

# Review Criteria
"""

        if criteria.check_code_quality:
            instruction += f"""
- **Code Quality**: Check SOLID principles, Clean Code practices, naming, complexity
  - Minimum acceptable score: {criteria.min_code_quality_score}/100
"""

        if criteria.check_tests:
            instruction += f"""
- **Tests**: Check test coverage, quality, edge cases
  - Minimum acceptable score: {criteria.min_test_coverage_score}/100
"""

        if criteria.check_security:
            instruction += """
- **Security**: Check for vulnerabilities, injection risks, data exposure
"""

        if criteria.check_documentation:
            instruction += f"""
- **Documentation**: Check docstrings, comments, clarity
  - Minimum acceptable score: {criteria.min_documentation_score}/100
"""

        if criteria.check_conventions:
            instruction += """
- **Conventions**: Check PEP 8, type hints, project patterns
"""

        if criteria.check_performance:
            instruction += """
- **Performance**: Check for performance issues, inefficiencies
"""

        instruction += f"""

# Diff to Review
```diff
{diff[:10000]}  # Limit to first 10k chars
```

# Your Task
Provide a thorough code review with the following structure:

## OUTCOME
State one of: APPROVED, REJECTED, NEEDS_CHANGES, UNCLEAR

## SUMMARY
One paragraph summary of your review

## ISSUES (Blocking)
List critical problems that MUST be fixed before merge:
- Issue 1
- Issue 2
"""

        if include_suggestions:
            instruction += """
## SUGGESTIONS (Non-blocking)
List improvements that would be nice but not required:
- Suggestion 1
- Suggestion 2
"""

        instruction += """
## SECURITY_CONCERNS
List any security vulnerabilities (critical):
- Concern 1 (if any)

## SCORES (0-100)
- Code Quality: X/100
- Test Coverage: X/100
- Documentation: X/100

## CONFIDENCE
Your confidence in this review (0.0-1.0): X.X

Be thorough, specific, and constructive. Focus on facts, not opinions.
"""

        return instruction

    def _review_with_model(
        self,
        instruction: str,
        model_type: str,
        model_name: str,
    ) -> ReviewResult:
        """
        Get review from specific auggie model.

        Args:
            instruction: Review instruction
            model_type: "gpt5" or "claude"
            model_name: Human-readable model name

        Returns:
            ReviewResult from this model

        Raises:
            PRReviewError: If auggie fails
        """
        # Write instruction to temp file (following dogfooding directive)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            prefix=".auggie_pr_review_",
            delete=False,
            dir=self.working_dir,
        ) as f:
            f.write(instruction)
            instruction_file = f.name

        try:
            # Call auggie via subprocess (MCP not available in this context)
            # Note: In real usage, would use MCP tools, but subprocess is more reliable here
            if model_type == "gpt5":
                cmd = [
                    "auggie",
                    "--instruction-file",
                    instruction_file,
                    "--model",
                    "gpt5",
                    "--quiet",
                ]
            else:  # claude
                cmd = [
                    "auggie",
                    "--instruction-file",
                    instruction_file,
                    "--model",
                    "sonnet4.5",
                    "--quiet",
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=self.working_dir,  # Set working directory via cwd parameter
            )

            if result.returncode != 0:
                raise PRReviewError(f"Auggie ({model_name}) failed: {result.stderr}")

            # Parse auggie output into ReviewResult
            review_text = result.stdout
            return self._parse_review_output(review_text, model_name)

        except subprocess.TimeoutExpired:
            raise PRReviewError(f"Auggie ({model_name}) timed out after {self.timeout_seconds}s")
        except Exception as e:
            raise PRReviewError(f"Auggie ({model_name}) failed: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(instruction_file):
                os.unlink(instruction_file)

    def _parse_review_output(self, review_text: str, reviewer_name: str) -> ReviewResult:
        """
        Parse auggie output into ReviewResult.

        Args:
            review_text: Raw auggie output
            reviewer_name: Model name

        Returns:
            ReviewResult

        Raises:
            PRReviewError: If parsing fails
        """
        try:
            # Extract outcome
            outcome_match = re.search(r"OUTCOME[:\s]+(\w+)", review_text, re.IGNORECASE)
            if outcome_match:
                outcome_str = outcome_match.group(1).upper()
                outcome = {
                    "APPROVED": ReviewOutcome.APPROVED,
                    "REJECTED": ReviewOutcome.REJECTED,
                    "NEEDS_CHANGES": ReviewOutcome.NEEDS_CHANGES,
                    "UNCLEAR": ReviewOutcome.UNCLEAR,
                }.get(outcome_str, ReviewOutcome.UNCLEAR)
            else:
                outcome = ReviewOutcome.UNCLEAR

            # Extract summary
            summary_match = re.search(
                r"SUMMARY[:\s]+(.*?)(?=##|\Z)", review_text, re.IGNORECASE | re.DOTALL
            )
            summary = summary_match.group(1).strip() if summary_match else "No summary provided"

            # Extract issues
            issues_match = re.search(
                r"ISSUES.*?(?=##|\Z)", review_text, re.IGNORECASE | re.DOTALL
            )
            issues = self._extract_list_items(issues_match.group(0)) if issues_match else []

            # Extract suggestions
            suggestions_match = re.search(
                r"SUGGESTIONS.*?(?=##|\Z)", review_text, re.IGNORECASE | re.DOTALL
            )
            suggestions = (
                self._extract_list_items(suggestions_match.group(0)) if suggestions_match else []
            )

            # Extract security concerns
            security_match = re.search(
                r"SECURITY_CONCERNS.*?(?=##|\Z)", review_text, re.IGNORECASE | re.DOTALL
            )
            security_concerns = (
                self._extract_list_items(security_match.group(0)) if security_match else []
            )

            # Extract scores
            code_score = self._extract_score(review_text, "Code Quality")
            test_score = self._extract_score(review_text, "Test Coverage")
            doc_score = self._extract_score(review_text, "Documentation")

            # Extract confidence
            conf_match = re.search(r"CONFIDENCE[:\s]+([\d\.]+)", review_text, re.IGNORECASE)
            confidence = float(conf_match.group(1)) if conf_match else 0.7

            return ReviewResult.create(
                pr_number=0,  # Will be set by caller
                outcome=outcome,
                summary=summary,
                issues=issues,
                suggestions=suggestions,
                security_concerns=security_concerns,
                code_quality_score=code_score,
                test_coverage_score=test_score,
                documentation_score=doc_score,
                reviewer=reviewer_name,
                confidence=confidence,
            )

        except Exception as e:
            raise PRReviewError(f"Failed to parse review output: {e}")

    def _extract_list_items(self, text: str) -> list:
        """Extract list items from markdown list."""
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                item = line.lstrip("-*").strip()
                if item:
                    items.append(item)
        return items

    def _extract_score(self, text: str, score_name: str) -> int:
        """Extract numeric score from text."""
        pattern = f"{score_name}[:\\s]+(\\d+)"
        match = re.search(pattern, text, re.IGNORECASE)
        return int(match.group(1)) if match else 70  # Default to 70

    def _combine_reviews(
        self,
        pr: PullRequest,
        reviews: list,
        start_time: datetime,
    ) -> ReviewResult:
        """
        Combine multiple model reviews into single result.

        Requires consensus for approval.

        Args:
            pr: Pull Request
            reviews: List of ReviewResult from different models
            start_time: Review start time

        Returns:
            Combined ReviewResult
        """
        # Outcome: Approve only if ALL models approve
        all_approved = all(r.outcome == ReviewOutcome.APPROVED for r in reviews)
        any_rejected = any(r.outcome == ReviewOutcome.REJECTED for r in reviews)

        if all_approved:
            combined_outcome = ReviewOutcome.APPROVED
        elif any_rejected:
            combined_outcome = ReviewOutcome.REJECTED
        else:
            combined_outcome = ReviewOutcome.NEEDS_CHANGES

        # Combine issues (union of all issues)
        combined_issues = []
        for r in reviews:
            combined_issues.extend(r.issues)

        # Combine suggestions (union)
        combined_suggestions = []
        for r in reviews:
            combined_suggestions.extend(r.suggestions)

        # Combine security concerns (union)
        combined_security = []
        for r in reviews:
            combined_security.extend(r.security_concerns)

        # Scores: Use minimum (most conservative)
        min_code_score = min(r.code_quality_score for r in reviews)
        min_test_score = min(r.test_coverage_score for r in reviews)
        min_doc_score = min(r.documentation_score for r in reviews)

        # Confidence: Average
        avg_confidence = sum(r.confidence for r in reviews) / len(reviews)

        # Summary: Combine from all models
        summaries = [f"**{r.reviewer}**: {r.summary}" for r in reviews]
        combined_summary = "\n\n".join(summaries)

        # Review time
        review_time = int((datetime.now() - start_time).total_seconds())

        return ReviewResult.create(
            pr_number=pr.number,
            outcome=combined_outcome,
            summary=combined_summary,
            issues=list(set(combined_issues)),  # Remove duplicates
            suggestions=list(set(combined_suggestions)),
            security_concerns=list(set(combined_security)),
            code_quality_score=min_code_score,
            test_coverage_score=min_test_score,
            documentation_score=min_doc_score,
            reviewer="auggie-multi-model (GPT-5 + Claude 4.5)",
            confidence=avg_confidence,
            review_time_seconds=review_time,
        )
