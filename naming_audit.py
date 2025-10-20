#!/usr/bin/env python3
"""
Naming Audit Script - Automated naming compliance checker for Clean Code principles.

This script scans the entire codebase and identifies naming violations according to
the Clean Code naming ruleset by Robert C. Martin.

Usage:
    python naming_audit.py [--output-dir OUTPUT_DIR] [--verbose]

Outputs:
    - naming_violations_report.json: Detailed JSON report of all violations
    - naming_violations_summary.md: Human-readable summary report
"""

import ast
import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Set
import argparse
import logging


@dataclass
class NamingViolation:
    """Represents a single naming violation."""
    violation_type: str
    file_path: str
    line_number: Optional[int]
    current_name: str
    suggested_name: str
    severity: str  # critical, high, medium, low
    ruleset_reference: str
    description: str


class NamingAuditor:
    """Scans codebase for naming violations according to Clean Code principles."""

    def __init__(self, root_path: Path, verbose: bool = False):
        self.root_path = root_path
        self.violations: List[NamingViolation] = []
        self.logger = logging.getLogger(__name__)
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        
        # Common verbs for function naming (verb prefixes and standalone verbs)
        self.common_verbs = {
            # CRUD operations
            'get', 'set', 'create', 'delete', 'update', 'fetch', 'save', 'load',
            'insert', 'upsert', 'remove', 'add', 'append', 'push', 'pop', 'put',
            'read', 'write', 'edit', 'modify', 'change', 'alter', 'assign',

            # Query operations
            'find', 'search', 'filter', 'query', 'select', 'retrieve', 'lookup',
            'count', 'list', 'enumerate', 'index',

            # Transformation operations
            'process', 'transform', 'convert', 'parse', 'format', 'serialize',
            'deserialize', 'encode', 'decode', 'compress', 'decompress',
            'extract', 'replace', 'substitute', 'swap', 'rename', 'simplify',
            'optimize', 'deduplicate', 'dedup', 'normalize', 'denormalize',

            # Validation operations
            'validate', 'check', 'verify', 'test', 'assert', 'ensure', 'confirm',
            'approve', 'reject', 'accept', 'deny',

            # Computation operations
            'calculate', 'compute', 'evaluate', 'derive', 'determine',
            'measure', 'estimate', 'predict', 'forecast',

            # Analysis operations
            'analyze', 'audit', 'inspect', 'examine', 'review', 'assess',
            'diagnose', 'profile', 'debug', 'troubleshoot',

            # Comparison operations
            'compare', 'diff', 'match', 'equal', 'differ',

            # Generation operations
            'generate', 'build', 'make', 'construct', 'assemble', 'compose',
            'synthesize', 'produce', 'yield', 'emit',

            # Communication operations
            'send', 'receive', 'emit', 'publish', 'subscribe', 'notify', 'broadcast',
            'announce', 'signal', 'alert', 'warn',

            # Rendering operations
            'render', 'draw', 'display', 'show', 'print', 'output',
            'visualize', 'plot', 'graph',

            # Execution operations
            'execute', 'run', 'invoke', 'call', 'trigger', 'dispatch', 'apply',
            'launch', 'spawn', 'fork', 'implement', 'perform', 'do',

            # Lifecycle operations
            'start', 'stop', 'pause', 'resume', 'restart', 'init', 'initialize',
            'configure', 'setup', 'cleanup', 'teardown', 'shutdown', 'close', 'open',
            'destroy', 'dispose', 'finalize', 'reset', 'clear', 'flush',
            'complete', 'finish', 'end', 'terminate', 'transition', 'fail', 'succeed',

            # Management operations
            'handle', 'manage', 'control', 'monitor', 'watch', 'track',
            'maintain', 'coordinate', 'orchestrate', 'schedule', 'route',
            'direct', 'forward', 'redirect', 'dispatch',

            # Resource operations
            'allocate', 'deallocate', 'acquire', 'release', 'lock', 'unlock',
            'claim', 'relinquish', 'reserve', 'free', 'register', 'unregister',
            'subscribe', 'unsubscribe', 'bind', 'unbind', 'attach', 'detach',

            # Synchronization operations
            'sync', 'synchronize', 'wait', 'poll', 'block', 'unblock',
            'timeout', 'retry', 'cancel', 'abort',

            # Aggregation operations
            'collect', 'gather', 'aggregate', 'accumulate', 'merge', 'combine',
            'join', 'split', 'group', 'partition', 'chunk', 'batch', 'decompose',
            'disassemble', 'separate', 'divide',

            # Traversal operations
            'traverse', 'walk', 'visit', 'iterate', 'scan', 'explore',
            'navigate', 'browse', 'crawl',

            # Sorting operations
            'sort', 'order', 'rank', 'prioritize', 'organize',
            'arrange', 'reorder', 'shuffle',

            # Mapping operations
            'map', 'reduce', 'fold', 'unfold', 'zip', 'flatten',
            'expand', 'collapse', 'nest', 'unnest',

            # Resolution operations
            'resolve', 'lookup', 'dereference', 'expand', 'interpolate',

            # Modal verbs (can/should/must patterns)
            'can', 'could', 'should', 'would', 'will', 'must', 'may', 'might',

            # State verbs (is/has/exists patterns)
            'is', 'are', 'was', 'were', 'has', 'have', 'had', 'exists', 'contains',
            'includes', 'lacks', 'needs', 'requires',

            # Recording operations
            'record', 'log', 'register', 'report', 'capture', 'trace',
            'snapshot', 'checkpoint', 'backup', 'archive',

            # User interaction operations
            'prompt', 'ask', 'request', 'respond', 'reply', 'answer',
            'confirm', 'deny', 'cancel', 'submit',

            # Testing operations
            'mock', 'stub', 'spy', 'fake', 'simulate',

            # Planning operations
            'plan', 'prepare', 'design', 'draft', 'outline', 'spec', 'specify',

            # Support operations
            'support', 'supports', 'assist', 'help', 'aid',

            # Miscellaneous common verbs
            'clone', 'copy', 'duplicate', 'mirror', 'reflect',
            'skip', 'ignore', 'exclude', 'include', 'omit',
            'enable', 'disable', 'toggle', 'switch', 'activate', 'deactivate',
            'flatten', 'unflatten', 'wrap', 'unwrap', 'pack', 'unpack',
        }

        # Python idioms that are acceptable without explicit verbs
        # (Entry points, special patterns, dataclass methods)
        self.python_idioms = {
            'main',  # Standard entry point
            'to_dict', 'from_dict', 'to_json', 'from_json', 'to_string',
            'to_list', 'from_string', 'as_dict', 'as_json', 'as_list',
            'asdict', 'astuple',  # dataclasses methods
        }
        
        # Directories that are allowed to be plural
        self.allowed_plural_dirs = {
            'tests', 'docs', 'examples', 'scripts', 'configs', 'logs',
            'backups', 'results', 'benchmarks', 'workflows', 'secrets',
            'certs', 'htmlcov', 'node_modules', '__pycache__'
        }

    def audit_codebase(self) -> List[NamingViolation]:
        """Perform comprehensive naming audit of the codebase."""
        self.logger.info(f"Starting naming audit of {self.root_path}")
        
        # Audit directories
        self._audit_directories()
        
        # Audit Python files
        for py_file in self.root_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            self._audit_file_naming(py_file)
            self._audit_python_code(py_file)
        
        self.logger.info(f"Audit complete. Found {len(self.violations)} violations")
        return self.violations

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during audit."""
        skip_patterns = [
            '__pycache__', '.git', '.venv', 'venv', 'node_modules',
            '.pytest_cache', 'htmlcov', 'dist', 'build', '.egg-info'
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _audit_directories(self):
        """Audit directory naming violations."""
        for dirpath in self.root_path.rglob("*"):
            if not dirpath.is_dir() or self._should_skip_file(dirpath):
                continue
                
            dir_name = dirpath.name
            
            # Check for plural names (should be singular)
            if (dir_name.endswith('s') and 
                dir_name not in self.allowed_plural_dirs and
                len(dir_name) > 1):
                
                suggested = dir_name[:-1] if dir_name.endswith('s') else dir_name
                self.violations.append(NamingViolation(
                    violation_type="directory_plural",
                    file_path=str(dirpath.relative_to(self.root_path)),
                    line_number=None,
                    current_name=dir_name,
                    suggested_name=suggested,
                    severity="high",
                    ruleset_reference="Prefer Singular Names for Directories",
                    description=f"Directory '{dir_name}' uses plural form, should be singular"
                ))
            
            # Check for deep nesting (>4 levels)
            relative_path = dirpath.relative_to(self.root_path)
            depth = len(relative_path.parts)
            if depth > 4:
                self.violations.append(NamingViolation(
                    violation_type="directory_deep_nesting",
                    file_path=str(relative_path),
                    line_number=None,
                    current_name=str(relative_path),
                    suggested_name="Consider flattening directory structure",
                    severity="medium",
                    ruleset_reference="Avoid Deep Nesting and Ambiguity",
                    description=f"Directory nesting depth {depth} exceeds recommended 4 levels"
                ))
            
            # Check for ambiguous names
            ambiguous_names = {'misc', 'stuff', 'things', 'temp', 'tmp', 'other'}
            if dir_name.lower() in ambiguous_names:
                self.violations.append(NamingViolation(
                    violation_type="directory_ambiguous",
                    file_path=str(relative_path),
                    line_number=None,
                    current_name=dir_name,
                    suggested_name="Use descriptive name based on contents",
                    severity="high",
                    ruleset_reference="Be Descriptive and Specific",
                    description=f"Directory name '{dir_name}' is ambiguous and unclear"
                ))

    def _audit_file_naming(self, file_path: Path):
        """Audit file naming violations."""
        file_name = file_path.stem  # filename without extension
        
        # Check for non-snake_case in Python files
        if not self._is_snake_case(file_name) and file_name != '__init__':
            suggested = self._to_snake_case(file_name)
            self.violations.append(NamingViolation(
                violation_type="file_not_snake_case",
                file_path=str(file_path.relative_to(self.root_path)),
                line_number=None,
                current_name=file_name,
                suggested_name=suggested,
                severity="medium",
                ruleset_reference="Use Consistent Casing and Style",
                description=f"Python file '{file_name}' should use snake_case naming"
            ))
        
        # Check for cryptic names (single letters, very short names)
        if len(file_name) <= 2 and file_name not in ['__init__', 'py']:
            self.violations.append(NamingViolation(
                violation_type="file_cryptic_name",
                file_path=str(file_path.relative_to(self.root_path)),
                line_number=None,
                current_name=file_name,
                suggested_name="Use descriptive name based on file purpose",
                severity="high",
                ruleset_reference="Choose Descriptive and Unambiguous Names",
                description=f"File name '{file_name}' is too short and cryptic"
            ))

    def _audit_python_code(self, file_path: Path):
        """Audit Python code for function and variable naming violations."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            self._audit_ast_node(tree, file_path, content.splitlines())
            
        except (SyntaxError, UnicodeDecodeError) as e:
            self.logger.warning(f"Could not parse {file_path}: {e}")

    def _audit_ast_node(self, node: ast.AST, file_path: Path, lines: List[str]):
        """Recursively audit AST nodes for naming violations."""
        for child in ast.walk(node):
            if isinstance(child, ast.FunctionDef):
                self._audit_function(child, file_path, lines)
            elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                self._audit_variable(child, file_path, lines)

    def _audit_function(self, func_node: ast.FunctionDef, file_path: Path, lines: List[str]):
        """Audit function naming violations."""
        func_name = func_node.name
        
        # Skip special methods
        if func_name.startswith('__') and func_name.endswith('__'):
            return
        
        # Check for verb-noun pattern
        if not self._has_verb_noun_pattern(func_name) and not func_name.startswith('_'):
            suggested = self._suggest_verb_noun_name(func_name)
            self.violations.append(NamingViolation(
                violation_type="function_no_verb_noun",
                file_path=str(file_path.relative_to(self.root_path)),
                line_number=func_node.lineno,
                current_name=func_name,
                suggested_name=suggested,
                severity="medium",
                ruleset_reference="Form Verb-Noun Pairs",
                description=f"Function '{func_name}' should follow verb-noun pattern"
            ))
        
        # Check for boolean flag arguments
        if self._has_boolean_flag_args(func_node):
            self.violations.append(NamingViolation(
                violation_type="function_boolean_flag",
                file_path=str(file_path.relative_to(self.root_path)),
                line_number=func_node.lineno,
                current_name=func_name,
                suggested_name=f"Split into separate functions (e.g., {func_name}_for_web, {func_name}_for_console)",
                severity="high",
                ruleset_reference="Avoid Flag Arguments",
                description=f"Function '{func_name}' has boolean flag arguments, should be split"
            ))

    def _audit_variable(self, var_node: ast.Name, file_path: Path, lines: List[str]):
        """Audit variable naming violations."""
        var_name = var_node.id
        
        # Check for single-letter variables in large scopes
        if len(var_name) == 1 and var_name not in ['i', 'j', 'k', 'x', 'y', 'z']:
            # This is a simplified check - in practice, we'd need scope analysis
            self.violations.append(NamingViolation(
                violation_type="variable_single_letter",
                file_path=str(file_path.relative_to(self.root_path)),
                line_number=var_node.lineno,
                current_name=var_name,
                suggested_name="Use descriptive name based on purpose",
                severity="low",
                ruleset_reference="Scale Length with Scope",
                description=f"Single-letter variable '{var_name}' should have descriptive name"
            ))
        
        # Check for Hungarian notation
        if self._has_hungarian_notation(var_name):
            suggested = self._remove_hungarian_notation(var_name)
            self.violations.append(NamingViolation(
                violation_type="variable_hungarian_notation",
                file_path=str(file_path.relative_to(self.root_path)),
                line_number=var_node.lineno,
                current_name=var_name,
                suggested_name=suggested,
                severity="medium",
                ruleset_reference="Avoid Encodings",
                description=f"Variable '{var_name}' uses Hungarian notation, should be '{suggested}'"
            ))

    def _is_snake_case(self, name: str) -> bool:
        """Check if name follows snake_case convention."""
        return re.match(r'^[a-z][a-z0-9_]*$', name) is not None

    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case."""
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _has_verb_noun_pattern(self, func_name: str) -> bool:
        """Check if function name follows verb-noun pattern.

        Accepts:
        1. Functions starting with a verb: get_user(), can_handle(), is_valid()
        2. Functions that ARE a single verb: compose(), execute(), validate()
        3. Python idioms: to_dict(), from_dict(), as_json()
        """
        func_lower = func_name.lower()

        # Check for Python idioms first (exact match)
        if func_lower in self.python_idioms:
            return True

        # Check if function IS a single verb (no underscore, entire name is a verb)
        if '_' not in func_name and func_lower in self.common_verbs:
            return True

        # Check if function starts with a verb followed by underscore (verb_noun pattern)
        if '_' in func_name:
            first_word = func_name.split('_')[0].lower()
            if first_word in self.common_verbs:
                return True

        return False

    def _suggest_verb_noun_name(self, func_name: str) -> str:
        """Suggest a verb-noun name for a function.

        Provides intelligent suggestions based on function name patterns.
        """
        func_lower = func_name.lower()

        # Handle test functions
        if 'test' in func_lower:
            return f"test_{func_name.replace('test', '').strip('_')}"

        # Suggest based on common patterns
        if any(keyword in func_lower for keyword in ['valid', 'check', 'verify']):
            return f"validate_{func_name}"
        elif any(keyword in func_lower for keyword in ['data', 'info', 'result']):
            return f"get_{func_name}"
        elif any(keyword in func_lower for keyword in ['config', 'setting', 'option']):
            return f"configure_{func_name}"
        elif any(keyword in func_lower for keyword in ['error', 'exception', 'failure']):
            return f"handle_{func_name}"
        elif func_name.endswith('s'):  # Possibly plural (e.g., users → get_users)
            return f"get_{func_name}"

        # Default: suggest processing
        return f"process_{func_name}"

    def _has_boolean_flag_args(self, func_node: ast.FunctionDef) -> bool:
        """Check if function has boolean flag arguments."""
        for arg in func_node.args.args:
            # This is a simplified check - would need type analysis for better detection
            if any(keyword in arg.arg.lower() for keyword in ['is_', 'has_', 'should_', 'flag', 'enable']):
                return True
        return False

    def _has_hungarian_notation(self, var_name: str) -> bool:
        """Check if variable uses Hungarian notation.

        True Hungarian notation has type prefixes followed by:
        - An underscore: str_name, int_count
        - Or uppercase letter: strName, intCount

        NOT Hungarian notation:
        - strategy (starts with 'str' but it's part of the word)
        - integration (starts with 'int' but it's part of the word)
        """
        # Type prefixes that indicate Hungarian notation
        type_prefixes = ['str', 'int', 'bool', 'float', 'list', 'dict', 'tuple', 'set', 'obj']
        # Scope prefixes (member/global)
        scope_prefixes = ['m_', 'g_', 's_', 'c_']

        # Check scope prefixes (they always have underscore)
        for prefix in scope_prefixes:
            if var_name.startswith(prefix):
                return True

        # Check type prefixes (must be followed by underscore or uppercase)
        for prefix in type_prefixes:
            # Pattern 1: str_name, int_count (underscore after prefix)
            if var_name.lower().startswith(prefix + '_'):
                return True
            # Pattern 2: strName, intCount (uppercase after prefix)
            if (var_name.startswith(prefix) and
                len(var_name) > len(prefix) and
                var_name[len(prefix)].isupper()):
                return True

        return False

    def _remove_hungarian_notation(self, var_name: str) -> str:
        """Remove Hungarian notation from variable name.

        Examples:
        - str_name → name
        - strName → name
        - m_count → count
        """
        type_prefixes = ['str', 'int', 'bool', 'float', 'list', 'dict', 'tuple', 'set', 'obj']
        scope_prefixes = ['m_', 'g_', 's_', 'c_']

        # Remove scope prefixes (always with underscore)
        for prefix in scope_prefixes:
            if var_name.startswith(prefix):
                return var_name[len(prefix):]

        # Remove type prefixes (underscore or camelCase)
        for prefix in type_prefixes:
            # Pattern 1: str_name → name
            if var_name.lower().startswith(prefix + '_'):
                return var_name[len(prefix) + 1:]
            # Pattern 2: strName → name
            if (var_name.startswith(prefix) and
                len(var_name) > len(prefix) and
                var_name[len(prefix)].isupper()):
                # Convert first letter to lowercase: strName → name
                remainder = var_name[len(prefix):]
                return remainder[0].lower() + remainder[1:] if remainder else var_name

        return var_name


def generate_reports(violations: List[NamingViolation], output_dir: Path):
    """Generate JSON and Markdown reports from violations."""
    
    # Generate JSON report
    json_report = {
        "summary": {
            "total_violations": len(violations),
            "by_severity": {
                "critical": len([v for v in violations if v.severity == "critical"]),
                "high": len([v for v in violations if v.severity == "high"]),
                "medium": len([v for v in violations if v.severity == "medium"]),
                "low": len([v for v in violations if v.severity == "low"])
            },
            "by_type": {}
        },
        "violations": [asdict(v) for v in violations]
    }
    
    # Count by type
    for violation in violations:
        vtype = violation.violation_type
        json_report["summary"]["by_type"][vtype] = json_report["summary"]["by_type"].get(vtype, 0) + 1
    
    # Write JSON report
    json_path = output_dir / "naming_violations_report.json"
    with open(json_path, 'w') as f:
        json.dump(json_report, f, indent=2)
    
    # Generate Markdown summary
    md_content = generate_markdown_summary(violations, json_report["summary"])
    md_path = output_dir / "naming_violations_summary.md"
    with open(md_path, 'w') as f:
        f.write(md_content)
    
    print(f"Reports generated:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")


def generate_markdown_summary(violations: List[NamingViolation], summary: Dict) -> str:
    """Generate human-readable Markdown summary."""
    md = "# Naming Violations Report\n\n"
    md += f"**Generated:** {os.popen('date').read().strip()}\n\n"
    
    md += "## Summary\n\n"
    md += f"- **Total Violations:** {summary['total_violations']}\n"
    md += f"- **Critical:** {summary['by_severity']['critical']}\n"
    md += f"- **High:** {summary['by_severity']['high']}\n"
    md += f"- **Medium:** {summary['by_severity']['medium']}\n"
    md += f"- **Low:** {summary['by_severity']['low']}\n\n"
    
    md += "## Violations by Type\n\n"
    for vtype, count in summary['by_type'].items():
        md += f"- **{vtype.replace('_', ' ').title()}:** {count}\n"
    md += "\n"
    
    # Group violations by severity
    for severity in ['critical', 'high', 'medium', 'low']:
        severity_violations = [v for v in violations if v.severity == severity]
        if not severity_violations:
            continue
            
        md += f"## {severity.title()} Priority Violations\n\n"
        for violation in severity_violations[:10]:  # Limit to first 10 per severity
            md += f"### {violation.current_name}\n"
            md += f"- **File:** `{violation.file_path}`\n"
            if violation.line_number:
                md += f"- **Line:** {violation.line_number}\n"
            md += f"- **Issue:** {violation.description}\n"
            md += f"- **Suggested:** `{violation.suggested_name}`\n"
            md += f"- **Rule:** {violation.ruleset_reference}\n\n"
        
        if len(severity_violations) > 10:
            md += f"*... and {len(severity_violations) - 10} more {severity} violations*\n\n"
    
    return md


def main():
    """Main entry point for the naming audit script."""
    parser = argparse.ArgumentParser(description="Audit codebase for naming violations")
    parser.add_argument("--output-dir", type=Path, default=Path("."), 
                       help="Output directory for reports")
    parser.add_argument("--verbose", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    args.output_dir.mkdir(exist_ok=True)
    
    # Run audit
    auditor = NamingAuditor(Path("."), verbose=args.verbose)
    violations = auditor.audit_codebase()
    
    # Generate reports
    generate_reports(violations, args.output_dir)
    
    print(f"\nAudit complete! Found {len(violations)} naming violations.")
    print("Check the generated reports for details.")


if __name__ == "__main__":
    main()
