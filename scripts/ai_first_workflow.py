#!/usr/bin/env python3
"""
AI-First Development Accelerator using Qwen + ATADO.

This orchestrates the complete feature development lifecycle:
1. Research (Qwen)
2. Design (Qwen)
3. Implementation (Qwen generates, human validates)
4. Testing (ATADO multi-agent)
5. Documentation (Qwen)
"""

import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.factories.provider_factory import ProviderFactory


class AIFirstWorkflow:
    """Orchestrate AI-first feature development."""

    def __init__(self, feature_id: str, feature_spec: Dict):
        self.feature_id = feature_id
        self.spec = feature_spec
        self.factory = ProviderFactory()
        self.qwen = self._create_qwen_provider()
        self.output_dir = Path(__file__).parent.parent / "ai_development" / feature_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _create_qwen_provider(self):
        """Create Qwen provider with Thinking mode."""
        config = {
            "model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
            "thinking_mode": False
        }
        return self.factory.create_provider("qwen-agent", config)

    def phase1_research(self) -> str:
        """Phase 1: Research best practices and approaches."""
        print(f"\n{'='*70}")
        print(f"PHASE 1: RESEARCH - {self.spec['title']}")
        print(f"{'='*70}\n")

        prompt = f"""Research task for feature development.

FEATURE: {self.spec['title']}

DESCRIPTION:
{self.spec.get('description', '')}

RESEARCH TASKS:
1. Identify best practices for this type of feature
2. Survey existing implementations (libraries, frameworks)
3. Analyze trade-offs between different approaches
4. Recommend optimal approach with justification

DELIVERABLES:
- Summary of best practices (3-5 key points)
- Comparison of 2-3 approaches with pros/cons
- Recommended approach with detailed rationale
- Key risks and mitigation strategies

USE THINKING MODE: This requires careful analysis."""

        print("🔍 Running research phase with Qwen...")
        start = time.time()
        result = self.qwen.generate(prompt)
        duration = time.time() - start

        # Save research output
        output_file = self.output_dir / "01_research.md"
        self._save_output(output_file, result, "Research Phase")

        print(f"✅ Research complete ({duration:.1f}s)")
        print(f"📄 Output saved: {output_file}")

        return result

    def phase2_design(self, research_output: str) -> str:
        """Phase 2: Create architecture and design."""
        print(f"\n{'='*70}")
        print(f"PHASE 2: DESIGN - {self.spec['title']}")
        print(f"{'='*70}\n")

        # Extract content from Qwen response
        research_content = self._extract_content(research_output)

        prompt = f"""Design architecture for feature implementation.

FEATURE: {self.spec['title']}

RESEARCH FINDINGS:
{research_content[:2000]}

DESIGN TASKS:
1. Create high-level architecture diagram (ASCII or Mermaid)
2. Define component responsibilities
3. Specify interfaces and data flow
4. Identify integration points with existing system
5. Plan for testing (unit, integration, e2e)

DELIVERABLES:
- Architecture diagram
- Component specifications
- API/interface definitions
- Integration plan
- Test strategy

CONSTRAINTS:
- Must follow Clean Architecture (entities, use cases, adapters)
- Must be backward compatible
- Must have 90%+ test coverage

USE THINKING MODE: Design requires careful planning."""

        print("🏗️  Running design phase with Qwen...")
        start = time.time()
        result = self.qwen.generate(prompt)
        duration = time.time() - start

        output_file = self.output_dir / "02_design.md"
        self._save_output(output_file, result, "Design Phase")

        print(f"✅ Design complete ({duration:.1f}s)")
        print(f"📄 Output saved: {output_file}")

        return result

    def phase3_implementation(self, design_output: str) -> Dict[str, str]:
        """Phase 3: Generate implementation code."""
        print(f"\n{'='*70}")
        print(f"PHASE 3: IMPLEMENTATION - {self.spec['title']}")
        print(f"{'='*70}\n")

        design_content = self._extract_content(design_output)

        # Generate main implementation
        impl_prompt = f"""Generate Python implementation for this feature.

FEATURE: {self.spec['title']}

DESIGN:
{design_content[:3000]}

IMPLEMENTATION TASKS:
1. Create main implementation file(s)
2. Follow Clean Architecture (separate concerns)
3. Add comprehensive docstrings (Google style)
4. Include error handling
5. Add type hints

DELIVERABLES:
- Complete, working Python code
- Proper imports and dependencies
- Error handling
- Docstrings for all public functions/classes

CODE QUALITY REQUIREMENTS:
- PEP 8 compliant
- Functions <20 lines (SRP)
- Clear, descriptive names
- No TODOs or placeholders

IMPORTANT: Output the code in a markdown code block like this:
```python
# Your code here
```

Do NOT include any thinking process or explanations. ONLY the code block."""

        print("💻 Generating implementation code...")
        start = time.time()
        impl_code = self.qwen.generate(impl_prompt)
        impl_duration = time.time() - start

        impl_file = self.output_dir / "03_implementation.py"
        self._save_output(impl_file, impl_code, "Implementation Code")

        print(f"✅ Implementation generated ({impl_duration:.1f}s)")

        # Extract actual code
        impl_content = self._extract_content(impl_code)

        # Generate tests
        test_prompt = f"""Generate comprehensive tests for this implementation.

FEATURE: {self.spec['title']}

IMPLEMENTATION:
{impl_content[:3000]}

TEST TASKS:
1. Create pytest test suite
2. Cover happy path scenarios
3. Cover edge cases and error conditions
4. Use mocking where appropriate
5. Aim for 90%+ coverage

DELIVERABLES:
- Complete pytest test file
- Fixtures for common test data
- Parametrized tests where applicable
- Clear test names (test_<behavior>_when_<condition>)

IMPORTANT: Output the code in a markdown code block like this:
```python
# Your test code here
```

Do NOT include any thinking process or explanations. ONLY the code block."""

        print("🧪 Generating test code...")
        start = time.time()
        test_code = self.qwen.generate(test_prompt)
        test_duration = time.time() - start

        test_file = self.output_dir / "test_03_implementation.py"
        self._save_output(test_file, test_code, "Test Code")

        print(f"✅ Tests generated ({test_duration:.1f}s)")

        return {
            "implementation": str(impl_file),
            "tests": str(test_file)
        }

    def phase4_validation(self, code_files: Dict[str, str]) -> bool:
        """Phase 4: Validate generated code."""
        print(f"\n{'='*70}")
        print(f"PHASE 4: VALIDATION - {self.spec['title']}")
        print(f"{'='*70}\n")

        print("🔍 Running static analysis...")

        # Check syntax of implementation
        impl_file = code_files["implementation"]
        result = subprocess.run(
            ["python3", "-m", "py_compile", impl_file],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"❌ Syntax error in implementation:")
            print(result.stderr)
            return False

        print("✅ Implementation syntax valid")

        # Check test syntax
        test_file = code_files["tests"]
        result = subprocess.run(
            ["python3", "-m", "py_compile", test_file],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"❌ Syntax error in tests:")
            print(result.stderr)
            return False

        print("✅ Test syntax valid")

        print("\n📋 HUMAN REVIEW REQUIRED:")
        print(f"   1. Review implementation: {impl_file}")
        print(f"   2. Review tests: {test_file}")
        print(f"   3. Run tests manually: pytest {test_file}")
        print(f"   4. Check for edge cases and error handling")

        return True

    def phase5_documentation(self, implementation_files: Dict[str, str]) -> str:
        """Phase 5: Generate documentation."""
        print(f"\n{'='*70}")
        print(f"PHASE 5: DOCUMENTATION - {self.spec['title']}")
        print(f"{'='*70}\n")

        prompt = f"""Generate comprehensive documentation for this feature.

FEATURE: {self.spec['title']}

IMPLEMENTATION FILES:
- {implementation_files['implementation']}
- {implementation_files['tests']}

DOCUMENTATION TASKS:
1. Feature overview and purpose
2. Usage examples (3-5 examples)
3. API reference (functions, classes, parameters)
4. Integration guide (how to use in ATADO)
5. Testing guide (how to run tests)

DELIVERABLES:
- Complete markdown documentation
- Code examples
- Troubleshooting section

FORMAT: GitHub-flavored markdown with code blocks."""

        print("📝 Generating documentation...")
        start = time.time()
        doc = self.qwen.generate(prompt)
        duration = time.time() - start

        doc_file = self.output_dir / "04_documentation.md"
        self._save_output(doc_file, doc, "Documentation")

        print(f"✅ Documentation generated ({duration:.1f}s)")
        print(f"📄 Output saved: {doc_file}")

        return doc

    def _extract_content(self, response: str) -> str:
        """Extract content from Qwen-Agent response format."""
        if isinstance(response, str) and response.startswith("[{"):
            import ast
            try:
                response_list = ast.literal_eval(response)
                if response_list and isinstance(response_list, list):
                    return response_list[0].get('content', response)
            except:
                pass
        return response

    def _extract_code_from_markdown(self, content: str) -> str:
        """Extract code from markdown code blocks."""
        import re
        # Look for ```python ... ``` blocks
        pattern = r'```python\s*\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        if matches:
            return matches[0].strip()
        return content.strip()

    def _save_output(self, file_path: Path, content: str, phase_name: str):
        """Save output to file with metadata."""
        # Extract content from Qwen-Agent response format
        content = self._extract_content(content)

        # For Python files, extract from markdown and add metadata as comments
        if file_path.suffix == '.py':
            actual_code = self._extract_code_from_markdown(content)

            with open(file_path, 'w') as f:
                f.write(f"# {phase_name}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write(f"# Feature: {self.spec['title']}\n")
                f.write(f"\n")
                f.write(actual_code)
        else:
            # For non-Python files (markdown), use regular format
            with open(file_path, 'w') as f:
                f.write(f"# {phase_name}\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"Feature: {self.spec['title']}\n")
                f.write(f"\n{'='*70}\n\n")
                f.write(content)

    def run_complete_workflow(self) -> bool:
        """Run complete AI-first development workflow."""
        print(f"\n{'#'*70}")
        print(f"# AI-FIRST DEVELOPMENT: {self.spec['title']}")
        print(f"{'#'*70}\n")

        start_time = time.time()

        try:
            # Phase 1: Research
            research = self.phase1_research()

            # Phase 2: Design
            design = self.phase2_design(research)

            # Phase 3: Implementation
            code_files = self.phase3_implementation(design)

            # Phase 4: Validation
            valid = self.phase4_validation(code_files)

            if not valid:
                print("\n❌ Validation failed - human review required")
                return False

            # Phase 5: Documentation
            self.phase5_documentation(code_files)

            total_time = time.time() - start_time

            print(f"\n{'='*70}")
            print("✅ AI-FIRST WORKFLOW COMPLETE!")
            print(f"{'='*70}")
            print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
            print(f"Output directory: {self.output_dir}")
            print(f"\nNext steps:")
            print(f"1. Review all generated files in {self.output_dir}")
            print(f"2. Run tests: pytest {self.output_dir}/test_*.py")
            print(f"3. Refine as needed")
            print(f"4. Integrate into main codebase")

            return True

        except Exception as e:
            print(f"\n❌ Workflow failed: {e}")
            import traceback
            traceback.print_exc()
            return False


# Feature specifications
FEATURES = {
    "p2_testing": {
        "title": "P2 Testing Infrastructure",
        "description": """
Setup comprehensive testing infrastructure for DSL runtime and CLI.

Requirements:
- pytest-cov integration
- DSL workflow integration tests
- Mock CLI adapter for testing
- Multi-agent orchestration tests
- Target: 90%+ test coverage

Current state: 131/134 tests passing (98%)
        """,
        "priority": "HIGH",
        "estimated_hours_manual": 6
    },
    "type_checking": {
        "title": "Hindley-Milner Type Checking Integration",
        "description": """
Integrate existing HM type system with DSL runtime.

Requirements:
- Type inference in interpreter
- Runtime type validation
- Type error reporting
- Type annotations for workflows
- Documentation

Dependencies: p2_testing (need tests first)
        """,
        "priority": "MEDIUM",
        "estimated_hours_manual": 8
    }
}


def main():
    """Run AI-first workflow for specified feature."""

    if len(sys.argv) < 2:
        print("Usage: python3 ai_first_workflow.py <feature_id>")
        print(f"Available features: {', '.join(FEATURES.keys())}")
        sys.exit(1)

    feature_id = sys.argv[1]

    if feature_id not in FEATURES:
        print(f"❌ Unknown feature: {feature_id}")
        print(f"Available: {', '.join(FEATURES.keys())}")
        sys.exit(1)

    feature_spec = FEATURES[feature_id]

    print(f"Feature: {feature_spec['title']}")
    print(f"Priority: {feature_spec['priority']}")
    print(f"Estimated manual time: {feature_spec['estimated_hours_manual']} hours")
    print(f"\nStarting AI-first workflow...\n")

    workflow = AIFirstWorkflow(feature_id, feature_spec)
    success = workflow.run_complete_workflow()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
