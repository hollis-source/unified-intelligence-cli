"""Auggie CLI Executor for HTN Task Execution

Wrapper around auggie CLI that:
- Achieves 55-91x speedup via optimized configuration
- Captures reasoning and side effects
- Integrates with HTN execution framework

Based on research findings in docs/AUGGIE_OPTIMIZATION_RESEARCH.md
"""

import subprocess
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

from src.entity.htn.htn_node import HTNNode
from src.entity.htn.execution_result import HTNExecutionResult
from src.interface.agent_executor import IAgentExecutor


@dataclass
class AuggieConfig:
    """Auggie CLI configuration (SIMPLIFIED & OPTIMIZED)

    Achieves 12-60x speedup via minimal workspace.
    No artificial constraints - let auggie produce complete, quality results.

    Key optimization: Minimal workspace avoids 3-5 min indexing.
    Everything else: Let auggie handle naturally.
    """

    workspace_root: str = "/tmp/auggie_research"
    model: str = "sonnet4.5"  # Options: sonnet4.5, gpt5, sonnet4
    save_session: bool = False # Disable for automation

    def to_flags(self) -> List[str]:
        """Convert config to auggie CLI flags

        Returns:
            List of CLI arguments
        """
        flags = [
            "--print",                          # One-shot mode
            "--quiet",                          # Minimal output
            "--workspace-root", self.workspace_root,
            "--model", self.model
        ]

        if not self.save_session:
            flags.append("--dont-save-session")

        return flags


class AuggieCLIExecutor(IAgentExecutor):
    """Execute HTN tasks using optimized auggie CLI

    Performance:
    - 3.3s per task (sonnet4.5 + max-turns 1 + empty workspace)
    - 7.7s per task (gpt5 + minimal workspace)
    - 55-91x faster than full codebase execution

    Usage:
        >>> config = AuggieConfig(model="sonnet4.5")
        >>> executor = AuggieCLIExecutor(config)
        >>> node = HTNNode(task_id="research", description="Design RAG architecture")
        >>> result = executor.execute(node)
        >>> print(f"Completed in {result.duration_seconds:.2f}s")
    """

    def __init__(self, config: Optional[AuggieConfig] = None):
        """Initialize auggie executor

        Args:
            config: Auggie configuration (uses defaults if None)
        """
        self.config = config or AuggieConfig()
        self._setup_workspace()

    def _setup_workspace(self):
        """Create minimal workspace (once per executor)

        Creates workspace with single README.md to avoid empty workspace
        paradox (GPT-5 is 3x slower with empty workspace).
        """
        workspace = Path(self.config.workspace_root)
        workspace.mkdir(parents=True, exist_ok=True)

        # Minimal README to avoid empty workspace paradox
        readme = workspace / "README.md"
        if not readme.exists():
            readme.write_text(
                f"# Auggie Research Workspace\n\n"
                f"Optimized minimal workspace for fast auggie execution.\n"
                f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

    def execute(self, node: HTNNode) -> HTNExecutionResult:
        """Execute HTN task via auggie CLI

        Args:
            node: HTN node to execute

        Returns:
            HTNExecutionResult with reasoning and side effects

        Raises:
            No exceptions - failures captured in result.success = False
        """
        start_time = time.time()

        # Build auggie command
        cmd = ["auggie"] + self.config.to_flags() + [node.description]

        # Track files before execution (for side effect detection)
        files_before = set(self._list_workspace_files())

        try:
            # Execute auggie (no timeout - let it complete naturally)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                # NO timeout - we want complete research results
                cwd=self.config.workspace_root
            )

            # Parse output
            output = result.stdout.strip()
            success = result.returncode == 0
            error = result.stderr.strip() if result.returncode != 0 else None

            # Track files after execution
            files_after = set(self._list_workspace_files())

            # Calculate side effects
            side_effects = {
                "files_created": list(files_after - files_before),
                "files_modified": self._detect_modifications(files_before, files_after),
                "executor_type": ["auggie"],
                "model_used": [self.config.model],
                "auggie_output_length": [str(len(output))]
            }

            # Extract thinking summary (first 200 chars)
            thinking_summary = output[:200] if len(output) > 200 else output

            # Update node metadata
            node.metadata["auggie_output"] = output
            node.metadata["auggie_success"] = success
            node.metadata["auggie_model"] = self.config.model

            return HTNExecutionResult(
                node=node,
                success=success,
                timestamp=datetime.now().isoformat(),
                duration_seconds=time.time() - start_time,
                output=output,
                error=error,
                side_effects=side_effects,
                thinking_summary=thinking_summary
            )

        except Exception as e:
            return HTNExecutionResult(
                node=node,
                success=False,
                timestamp=datetime.now().isoformat(),
                duration_seconds=time.time() - start_time,
                side_effects={},
                error=f"Auggie execution failed: {str(e)}"
            )

    def _list_workspace_files(self) -> List[str]:
        """List all files in workspace

        Returns:
            List of relative file paths
        """
        workspace = Path(self.config.workspace_root)
        return [
            str(f.relative_to(workspace))
            for f in workspace.rglob("*")
            if f.is_file()
        ]

    def _detect_modifications(
        self,
        before: set,
        after: set
    ) -> List[str]:
        """Detect which existing files were modified

        Args:
            before: Set of files before execution
            after: Set of files after execution

        Returns:
            List of modified file paths

        Note:
            Currently returns empty list as auggie in --print mode
            typically doesn't modify files. Could enhance with mtime
            or content hash checking if needed.
        """
        # Files that exist in both sets (potentially modified)
        common = before & after

        # TODO: Check mtimes or content hashes to detect actual modifications
        # For now, assume no modifications in research tasks
        return []
