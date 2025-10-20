#!/usr/bin/env python3
"""
Quick script to generate Phase 1 tests using Qwen3-Next-80B-A3B-Instruct.
Uses the deployed HF Inference Endpoint.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.factories.provider_factory import ProviderFactory

def main():
    # Load integration plan
    plan_path = Path(__file__).parent.parent / "docs" / "P2_TESTING_INTEGRATION_PLAN.md"
    plan_content = plan_path.read_text()

    # Load Agent entity source
    agent_path = Path(__file__).parent.parent / "src" / "entity" / "agent.py"
    agent_source = agent_path.read_text()

    # Create Qwen provider
    factory = ProviderFactory()
    config = {
        "model": "Qwen/Qwen3-Next-80B-A3B-Instruct",
        "thinking_mode": False,
        "base_url": os.getenv("QWEN_ENDPOINT"),
        "api_key": os.getenv("HF_TOKEN")
    }
    provider = factory.create_provider("qwen-agent", config)

    prompt = f"""ultrathink: Generate ATADO-specific pytest test infrastructure for Phase 1.

INTEGRATION PLAN (for context):
{plan_content[:3000]}

ACTUAL AGENT SOURCE CODE:
```python
{agent_source}
```

Generate TWO files as markdown code blocks:

1. **tests/conftest.py** - Pytest fixtures for ATADO:
   - mock_text_generator (mock ITextGenerator interface)
   - sample_agent (Agent fixture with realistic config)
   - sample_task (Task fixture)
   - Use imports: from src.entity.agent import Agent, Task
   - Use unittest.mock for mocking

2. **tests/unit/entity/test_agent_comprehensive.py** - Comprehensive Agent tests:
   - Test Agent creation with all parameters
   - Test can_handle() method with fuzzy matching (0.6 threshold)
   - Test tier system (tier 1-3)
   - Test specialization and parent_agent
   - Use parametrized tests for multiple scenarios
   - 20+ test cases total

CRITICAL: Output ONLY Python code in markdown blocks like:

```python
# tests/conftest.py
<code here>
```

```python
# tests/unit/entity/test_agent_comprehensive.py
<code here>
```

NO explanations. NO thinking process in output. ONLY code blocks."""

    print("🤖 Generating Phase 1 tests with Qwen3...")
    print("=" * 80)

    response = provider.generate(prompt)

    print(response)
    print("=" * 80)
    print("\n✅ Generation complete!")

    # Save output
    output_path = Path(__file__).parent.parent / "ai_development" / "p2_testing" / "phase1_generated.txt"
    output_path.write_text(response)
    print(f"📄 Saved to: {output_path}")

if __name__ == "__main__":
    main()
