"""
Safety Governance for ATADO

Implements guardrails to prevent dangerous operations and ensure safe autonomous behavior.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SafetyViolation:
    """Represents a safety rule violation."""
    rule_id: str
    severity: str  # critical, high, medium, low
    message: str
    task_description: str
    metadata: Dict[str, Any]


class SafetyGovernance:
    """
    Enforces safety rules for autonomous task execution.
    
    Rules:
    - No destructive file operations without approval
    - No network operations to external hosts without approval
    - No database mutations without approval
    - No code execution from untrusted sources
    - No credential/secret exposure
    - No infinite loops or resource exhaustion
    """
    
    # Dangerous patterns (regex)
    DESTRUCTIVE_FILE_OPS = [
        r'\brm\s+-rf\b',
        r'\brmdir\b',
        r'\bdel\s+/[sS]\b',
        r'\bformat\b.*\bc:\b',
        r'os\.remove\(',
        r'shutil\.rmtree\(',
        r'Path\(.*\)\.unlink\(',
    ]
    
    NETWORK_OPS = [
        r'curl\s+http',
        r'wget\s+http',
        r'requests\.(get|post|put|delete)\(',
        r'urllib\.request',
        r'socket\.connect\(',
    ]
    
    DB_MUTATIONS = [
        r'\bDROP\s+TABLE\b',
        r'\bDELETE\s+FROM\b',
        r'\bTRUNCATE\b',
        r'\bUPDATE\s+.*\s+SET\b',
        r'\.delete\(\)',
        r'\.drop\(\)',
    ]
    
    CODE_EXECUTION = [
        r'\beval\(',
        r'\bexec\(',
        r'__import__\(',
        r'subprocess\.call\(',
        r'os\.system\(',
    ]
    
    SECRET_PATTERNS = [
        r'password\s*=\s*["\']',
        r'api[_-]?key\s*=\s*["\']',
        r'secret\s*=\s*["\']',
        r'token\s*=\s*["\']',
        r'AWS_SECRET_ACCESS_KEY',
    ]
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize safety governance.
        
        Args:
            strict_mode: If True, block all violations. If False, only warn.
        """
        self.strict_mode = strict_mode
        self.violations: List[SafetyViolation] = []
    
    def validate_task(self, task_description: str, metadata: Optional[Dict[str, Any]] = None) -> List[SafetyViolation]:
        """
        Validate a task against safety rules.
        
        Args:
            task_description: Task description or code to validate
            metadata: Additional context (e.g., user, approval status)
            
        Returns:
            List of violations (empty if safe)
        """
        violations = []
        metadata = metadata or {}
        
        # Check for destructive file operations
        for pattern in self.DESTRUCTIVE_FILE_OPS:
            if re.search(pattern, task_description, re.IGNORECASE):
                violations.append(SafetyViolation(
                    rule_id="destructive-file-op",
                    severity="critical",
                    message=f"Destructive file operation detected: {pattern}",
                    task_description=task_description[:100],
                    metadata=metadata
                ))
        
        # Check for network operations
        for pattern in self.NETWORK_OPS:
            if re.search(pattern, task_description, re.IGNORECASE):
                violations.append(SafetyViolation(
                    rule_id="network-op",
                    severity="high",
                    message=f"Network operation detected: {pattern}",
                    task_description=task_description[:100],
                    metadata=metadata
                ))
        
        # Check for database mutations
        for pattern in self.DB_MUTATIONS:
            if re.search(pattern, task_description, re.IGNORECASE):
                violations.append(SafetyViolation(
                    rule_id="db-mutation",
                    severity="critical",
                    message=f"Database mutation detected: {pattern}",
                    task_description=task_description[:100],
                    metadata=metadata
                ))
        
        # Check for code execution
        for pattern in self.CODE_EXECUTION:
            if re.search(pattern, task_description, re.IGNORECASE):
                violations.append(SafetyViolation(
                    rule_id="code-execution",
                    severity="high",
                    message=f"Dynamic code execution detected: {pattern}",
                    task_description=task_description[:100],
                    metadata=metadata
                ))
        
        # Check for secret exposure
        for pattern in self.SECRET_PATTERNS:
            if re.search(pattern, task_description, re.IGNORECASE):
                violations.append(SafetyViolation(
                    rule_id="secret-exposure",
                    severity="critical",
                    message=f"Potential secret exposure detected: {pattern}",
                    task_description=task_description[:100],
                    metadata=metadata
                ))
        
        # Log violations
        for v in violations:
            logger.warning(f"Safety violation: {v.rule_id} - {v.message}")
            self.violations.append(v)
        
        return violations
    
    def is_safe(self, task_description: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a task is safe to execute.
        
        Args:
            task_description: Task description or code
            metadata: Additional context
            
        Returns:
            True if safe, False if violations found
        """
        violations = self.validate_task(task_description, metadata)
        
        if not violations:
            return True
        
        # Check if any critical violations
        critical = [v for v in violations if v.severity == "critical"]
        
        if self.strict_mode:
            return len(violations) == 0
        else:
            return len(critical) == 0
    
    def get_violations(self, severity: Optional[str] = None) -> List[SafetyViolation]:
        """
        Get recorded violations, optionally filtered by severity.
        
        Args:
            severity: Filter by severity (critical, high, medium, low)
            
        Returns:
            List of violations
        """
        if severity:
            return [v for v in self.violations if v.severity == severity]
        return self.violations
    
    def clear_violations(self) -> None:
        """Clear recorded violations."""
        self.violations = []
    
    @staticmethod
    def sanitize_task_description(description: str) -> str:
        """
        Sanitize task description by removing potentially dangerous content.
        
        Args:
            description: Raw task description
            
        Returns:
            Sanitized description
        """
        # Remove inline code execution
        sanitized = re.sub(r'\beval\([^)]+\)', '[SANITIZED]', description)
        sanitized = re.sub(r'\bexec\([^)]+\)', '[SANITIZED]', sanitized)
        
        # Remove potential secrets
        sanitized = re.sub(r'(password|api[_-]?key|secret|token)\s*=\s*["\'][^"\']+["\']', r'\1=[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        return sanitized

