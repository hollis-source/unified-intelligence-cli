#!/usr/bin/env python3
"""
Generate Phase 3 tests: AgentTeam entity comprehensive tests.

Uses Qwen3-Next-80B-A3B-Instruct (direct instruction mode).

Phase 3 Focus:
- AgentTeam base class (creation, routing, methods)
- All 9 concrete team subclasses (routing logic)
- Parametrized routing scenarios
- Edge cases (empty teams, missing agents, etc.)

Expected: 30+ tests covering complex routing behaviors.
"""

import os
import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.factories.provider_factory import ProviderFactory


def extract_code_from_markdown(content: str) -> str:
    """Extract Python code from markdown code blocks."""
    pattern = r'```python\s*\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL)
    if matches:
        return matches[0].strip()
    return content.strip()


def main():
    print("=" * 80)
    print("Phase 3: AgentTeam Entity Test Generation")
    print("=" * 80)

    # Read AgentTeam source code
    agent_team_path = project_root / "src/entity/agent_team.py"
    with open(agent_team_path, 'r') as f:
        agent_team_source = f.read()

    # Read Agent source (dependency)
    agent_path = project_root / "src/entity/agent.py"
    with open(agent_path, 'r') as f:
        agent_source = f.read()

    print("\n📖 Source Code Analysis:")
    print(f"   AgentTeam: {len(agent_team_source)} chars, {len(agent_team_source.splitlines())} lines")
    print(f"   Agent: {len(agent_source)} chars (dependency)")

    print("\n🔧 Entities to test:")
    print("   - AgentTeam (base class)")
    print("   - FrontendTeam")
    print("   - BackendTeam")
    print("   - TestingTeam")
    print("   - InfrastructureTeam")
    print("   - ResearchTeam")
    print("   - OrchestrationTeam")
    print("   - QualityAssuranceTeam")
    print("   - CategoryTheoryTeam")
    print("   - DSLTeam")

    # Initialize Qwen3 provider
    print("\n🚀 Initializing Qwen3-Next-80B-A3B-Instruct...")
    factory = ProviderFactory()
    config = {
        "model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
        "thinking_mode": False
    }

    try:
        provider = factory.create_provider("qwen-agent", config)
        print("   ✅ Provider initialized successfully")
    except Exception as e:
        print(f"   ❌ Provider initialization failed: {e}")
        return 1

    # Construct prompt
    prompt = f"""You are a Python testing expert. Generate comprehensive pytest tests for the AgentTeam entity.

**Source Code to Test:**

```python
{agent_team_source}
```

**Dependency (Agent entity):**

```python
{agent_source}
```

**Requirements:**

1. **Comprehensive Coverage** (30+ tests):
   - AgentTeam base class creation (name, domain, agents, lead_agent, tier)
   - route_internally() default behavior (lead delegation, fallback)
   - get_agent() method (role lookup)
   - can_handle() method (delegates to agents)
   - get_all_capabilities() method (combines agent capabilities)
   - __repr__() method (string representation)

2. **All 9 Concrete Teams** (3-5 tests each):
   - FrontendTeam: Design vs implementation routing
   - BackendTeam: Design vs implementation routing
   - TestingTeam: Strategy vs unit vs integration routing
   - InfrastructureTeam: Single-agent routing
   - ResearchTeam: Research vs documentation routing
   - OrchestrationTeam: Single-agent routing
   - QualityAssuranceTeam: Single-agent routing
   - CategoryTheoryTeam: Theory vs implementation routing
   - DSLTeam: Deployment vs task implementation routing

3. **Parametrized Tests**:
   - Use @pytest.mark.parametrize for routing scenarios
   - Cover all keyword branches in route_internally()
   - Test edge cases (empty descriptions, missing agents, etc.)

4. **Code Style**:
   - Use pytest fixtures from tests/conftest.py (sample_agent, sample_task)
   - Follow existing test patterns from test_agent_comprehensive.py
   - Import from src.entity.agent_team (NOT src.entities)
   - Use descriptive test names
   - Add docstrings explaining what each test validates

5. **Output Format**:
   - Return ONLY valid Python code
   - Enclose code in markdown ```python``` blocks
   - NO explanatory text outside code blocks
   - File should start with: # tests/unit/entity/test_agent_team_comprehensive.py

**Important Notes:**
- TestingTeam routing is complex: strategy→lead, unit→unit-engineer, integration→integration-engineer
- FrontendTeam/BackendTeam: design→lead, implementation→specialist
- Some teams are single-agent (route to lead always)
- Test both lead_agent present and missing scenarios
- Test get_agent() with missing roles

NO LONG THINKING. Focus on generating high-quality, executable tests. Return code immediately.

Generate the complete test file now:"""

    # Generate tests
    print("\n⏱️  Generating tests with Qwen3 (thinking mode enabled)...")
    print("   This may take 30-60 seconds due to complex routing logic...")

    try:
        import time
        start_time = time.time()

        response = provider.generate(prompt)

        elapsed = time.time() - start_time
        print(f"   ✅ Generation completed in {elapsed:.1f} seconds")

        # Extract thinking (if present)
        if hasattr(response, 'thinking') and response.thinking:
            thinking_chars = len(response.thinking)
            print(f"   🧠 Thinking: {thinking_chars} characters")

            # Save thinking to file for analysis
            thinking_path = project_root / "scripts/phase3_qwen_thinking.txt"
            with open(thinking_path, 'w') as f:
                f.write(response.thinking)
            print(f"   💾 Thinking saved to: {thinking_path}")

        # Extract code
        content = response.content if hasattr(response, 'content') else str(response)
        code = extract_code_from_markdown(content)

        print(f"\n📊 Generation Statistics:")
        print(f"   Raw output: {len(content)} characters")
        print(f"   Extracted code: {len(code)} characters")
        print(f"   Lines: {len(code.splitlines())}")

    except Exception as e:
        print(f"   ❌ Generation failed: {e}")
        return 1

    # Validate code structure
    print("\n🔍 Validating code structure...")
    if "import pytest" not in code:
        print("   ⚠️  WARNING: No pytest import found")
    if "def test_" not in code:
        print("   ⚠️  WARNING: No test functions found")
    if "src.entity.agent_team" not in code:
        print("   ⚠️  WARNING: Import path may be incorrect")

    test_count = code.count("def test_")
    fixture_count = code.count("@pytest.fixture")
    param_count = code.count("@pytest.mark.parametrize")

    print(f"   Test functions: {test_count}")
    print(f"   Fixtures: {fixture_count}")
    print(f"   Parametrized tests: {param_count}")

    if test_count < 20:
        print(f"   ⚠️  WARNING: Only {test_count} tests generated (expected 30+)")

    # Write to file
    output_path = project_root / "tests/unit/entity/test_agent_team_comprehensive.py"

    print(f"\n💾 Writing tests to: {output_path}")
    with open(output_path, 'w') as f:
        f.write(code)

    print("   ✅ File written successfully")

    # Instructions
    print("\n" + "=" * 80)
    print("✅ Phase 3 Test Generation Complete!")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Run tests: pytest tests/unit/entity/test_agent_team_comprehensive.py -v")
    print("2. Fix any errors found")
    print("3. Run coverage: pytest --cov=src/entity/agent_team tests/unit/entity/test_agent_team_comprehensive.py")
    print("\nExpected Result:")
    print("- 30+ tests passing")
    print("- High coverage of AgentTeam entity")
    print("- All routing behaviors validated")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
