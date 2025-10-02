"""Grok Analysis Tasks - AI-powered code review and analysis.

Clean Architecture: Use Cases layer (business logic for AI analysis).
SOLID: SRP - each task has one responsibility.

Uses Grok (grok-code-fast-1) for analyzing commits, code quality, patterns.
"""

import asyncio
import subprocess
from typing import Any, Dict, List
from pathlib import Path
import os


async def get_recent_commits(input_data: Any = None) -> Dict[str, Any]:
    """
    Get list of recent commits.

    Args:
        input_data: Optional dict with 'count' key (number of commits to fetch)

    Returns:
        List of commit hashes and messages
    """
    count = 10
    if isinstance(input_data, dict) and 'count' in input_data:
        count = input_data['count']

    result = subprocess.run(
        ["git", "log", f"-{count}", "--oneline"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    commits = []
    for line in result.stdout.strip().split('\n'):
        if line:
            parts = line.split(' ', 1)
            commits.append({
                "hash": parts[0],
                "message": parts[1] if len(parts) > 1 else ""
            })

    return {
        "task": "get_recent_commits",
        "status": "success",
        "commit_count": len(commits),
        "commits": commits
    }


async def get_commit_details(input_data: Any = None) -> Dict[str, Any]:
    """
    Get detailed commit information (diff, stats, files changed).

    Args:
        input_data: Dict with 'commits' key (list of commits from get_recent_commits)

    Returns:
        Detailed commit information with diffs
    """
    if not isinstance(input_data, dict) or 'commits' not in input_data:
        return {
            "task": "get_commit_details",
            "status": "error",
            "error": "No commits provided"
        }

    commits = input_data['commits']
    detailed_commits = []

    for commit in commits[:10]:  # Limit to 10 for performance
        commit_hash = commit['hash']

        # Get commit details
        show_result = subprocess.run(
            ["git", "show", commit_hash, "--stat"],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )

        # Get diff (limited)
        diff_result = subprocess.run(
            ["git", "show", commit_hash, "--no-stat"],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )

        detailed_commits.append({
            "hash": commit_hash,
            "message": commit['message'],
            "stat": show_result.stdout[:1000],  # Limit to 1KB
            "diff": diff_result.stdout[:5000]  # Limit to 5KB per commit
        })

    return {
        "task": "get_commit_details",
        "status": "success",
        "detailed_commits": detailed_commits
    }


async def analyze_commit_with_grok(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze a single commit using Grok AI.

    Args:
        input_data: Dict with commit details

    Returns:
        Grok's analysis of the commit
    """
    if not isinstance(input_data, dict):
        return {
            "task": "analyze_commit_with_grok",
            "status": "error",
            "error": "Invalid input"
        }

    # Check for Grok API key
    if not os.getenv('XAI_API_KEY'):
        return {
            "task": "analyze_commit_with_grok",
            "status": "skipped",
            "reason": "XAI_API_KEY not configured",
            "analysis": "Grok analysis requires XAI_API_KEY environment variable"
        }

    try:
        # Import provider here to avoid circular dependencies
        from src.factories.provider_factory import ProviderFactory

        # Create provider factory and get Grok provider
        factory = ProviderFactory()
        provider = factory.create_provider('grok', config=None)

        # Prepare analysis prompt
        commit_hash = input_data.get('hash', 'unknown')
        commit_message = input_data.get('message', '')
        diff = input_data.get('diff', '')[:4000]  # Limit diff size

        prompt = f"""Analyze this git commit and provide a comprehensive review:

Commit: {commit_hash}
Message: {commit_message}

Diff:
```
{diff}
```

Provide analysis covering:
1. **Purpose**: What does this commit achieve?
2. **Code Quality**: Clean Code principles (SRP, DRY, meaningful names)
3. **Architecture**: SOLID principles, design patterns
4. **Testing**: Test coverage, TDD practices
5. **Best Practices**: Follows Clean Agile, small commits
6. **Improvements**: Suggestions for future enhancements

Be concise but thorough. Focus on insights, not just description."""

        # Call Grok with proper message format
        messages = [{"role": "user", "content": prompt}]

        # GrokAdapter.generate() is synchronous, run in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, provider.generate, messages, None)

        return {
            "task": "analyze_commit_with_grok",
            "status": "success",
            "commit_hash": commit_hash,
            "commit_message": commit_message,
            "analysis": response
        }

    except Exception as e:
        return {
            "task": "analyze_commit_with_grok",
            "status": "error",
            "commit_hash": input_data.get('hash', 'unknown'),
            "error": str(e),
            "analysis": f"Analysis failed: {str(e)}"
        }


async def batch_analyze_commits(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze multiple commits with Grok (sequential to avoid rate limits).

    Args:
        input_data: Dict with 'detailed_commits' key

    Returns:
        List of analyses
    """
    if not isinstance(input_data, dict) or 'detailed_commits' not in input_data:
        return {
            "task": "batch_analyze_commits",
            "status": "error",
            "error": "No detailed commits provided"
        }

    detailed_commits = input_data['detailed_commits']
    analyses = []

    for commit in detailed_commits:
        analysis = await analyze_commit_with_grok(commit)
        analyses.append(analysis)

    return {
        "task": "batch_analyze_commits",
        "status": "success",
        "analyses": analyses
    }


async def aggregate_commit_analyses(input_data: Any = None) -> Dict[str, Any]:
    """
    Aggregate multiple commit analyses into summary.

    Args:
        input_data: Tuple of analyses from parallel execution

    Returns:
        Aggregated analysis summary
    """
    analyses = []

    # Handle tuple from parallel execution
    if isinstance(input_data, tuple):
        analyses = list(input_data)
    elif isinstance(input_data, list):
        analyses = input_data
    elif isinstance(input_data, dict) and 'analyses' in input_data:
        analyses = input_data['analyses']
    else:
        return {
            "task": "aggregate_commit_analyses",
            "status": "error",
            "error": "No analyses to aggregate"
        }

    successful = [a for a in analyses if a.get('status') == 'success']
    failed = [a for a in analyses if a.get('status') == 'error']
    skipped = [a for a in analyses if a.get('status') == 'skipped']

    return {
        "task": "aggregate_commit_analyses",
        "status": "success",
        "total_commits": len(analyses),
        "successful_analyses": len(successful),
        "failed_analyses": len(failed),
        "skipped_analyses": len(skipped),
        "analyses": successful
    }


async def generate_integrated_report(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate integrated commentary report from all analyses.

    Args:
        input_data: Aggregated analyses

    Returns:
        Comprehensive report with integrated commentary
    """
    if not isinstance(input_data, dict) or 'analyses' not in input_data:
        return {
            "task": "generate_integrated_report",
            "status": "error",
            "error": "No analyses provided"
        }

    analyses = input_data['analyses']

    report_lines = [
        "# Integrated Commit Analysis Report",
        f"**Generated**: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}",
        f"**Total Commits Analyzed**: {len(analyses)}",
        "",
        "---",
        ""
    ]

    # Add each commit analysis
    for i, analysis in enumerate(analyses, 1):
        commit_hash = analysis.get('commit_hash', 'unknown')
        commit_message = analysis.get('commit_message', '')
        grok_analysis = analysis.get('analysis', 'No analysis available')

        report_lines.extend([
            f"## {i}. Commit `{commit_hash}`",
            f"**Message**: {commit_message}",
            "",
            "### Grok Analysis",
            grok_analysis,
            "",
            "---",
            ""
        ])

    # Add summary section
    report_lines.extend([
        "## Overall Summary",
        "",
        f"Analyzed {len(analyses)} commits with Grok (grok-code-fast-1).",
        "",
        "### Key Themes:",
        "- Clean Code and SOLID principles application",
        "- DSL development and integration",
        "- Test-driven development practices",
        "- Clean Agile commit practices",
        "",
        "---",
        "*Generated via DSL + Grok integration*"
    ])

    report = "\n".join(report_lines)

    return {
        "task": "generate_integrated_report",
        "status": "success",
        "report": report,
        "file": "docs/GROK_COMMIT_ANALYSIS.md",
        "commit_count": len(analyses)
    }


async def save_report_to_file(input_data: Any = None) -> Dict[str, Any]:
    """
    Save report to markdown file.

    Args:
        input_data: Report data with 'report' and 'file' keys

    Returns:
        Save confirmation
    """
    if not isinstance(input_data, dict) or 'report' not in input_data:
        return {
            "task": "save_report_to_file",
            "status": "error",
            "error": "No report to save"
        }

    report = input_data['report']
    file_path = input_data.get('file', 'docs/GROK_COMMIT_ANALYSIS.md')

    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report)

        return {
            "task": "save_report_to_file",
            "status": "success",
            "file": str(path),
            "size_bytes": len(report),
            "recommendation": f"Review report at {file_path}"
        }

    except Exception as e:
        return {
            "task": "save_report_to_file",
            "status": "error",
            "error": str(e)
        }
