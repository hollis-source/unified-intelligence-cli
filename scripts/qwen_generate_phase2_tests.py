#!/usr/bin/env python3
"""
Generate Phase 2 tests using Qwen3: AgentTeam entity tests.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI

def main():
    # Setup client
    client = OpenAI(
        base_url=os.getenv("QWEN_ENDPOINT", "https://crlqq5n5zwaz4rnh.us-east-2.aws.endpoints.huggingface.cloud/v1"),
        api_key=os.getenv("HF_TOKEN")
    )

    # Load context files
    plan_path = Path(__file__).parent.parent / "docs" / "P2_TESTING_INTEGRATION_PLAN.md"
    plan_content = plan_path.read_text()[:3000]

    agent_team_path = Path(__file__).parent.parent / "src" / "entity" / "agent_team.py"
    agent_team_source = agent_team_path.read_text()

    prompt = f"""ultrathink: Generate comprehensive pytest tests for ATADO's AgentTeam entity.

INTEGRATION PLAN (excerpt):
{plan_content}

ACTUAL AGENTTEAM SOURCE CODE:
```python
{agent_team_source}
```

Generate ONE Python file in a markdown code block:

**tests/unit/entity/test_agent_team_comprehensive.py** - 20+ tests:
- Test AgentTeam creation (name, agents, lead_agent, domain)
- Test route_internally() method with different task types
- Test get_agent() method
- Test team agent management (add, remove, list)
- Use @pytest.mark.parametrize for routing scenarios
- Test concrete team implementations (FrontendTeam, BackendTeam, TestingTeam if they exist)

Use imports:
- from src.entity.agent_team import AgentTeam
- from src.entity.agent import Agent, Task
- import pytest

Output ONLY code in ```python block. No explanations."""

    print("🤖 Generating Phase 2 tests with Qwen3...")
    print("=" * 80)

    response = client.chat.completions.create(
        model="Qwen/Qwen3-Next-80B-A3B-Instruct",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.2
    )

    content = response.choices[0].message.content
    print(content)
    print("=" * 80)
    print(f"\n✅ Generated {len(content)} characters")

    # Save output
    output_path = Path(__file__).parent.parent / "ai_development" / "p2_testing" / "phase2_qwen_output.txt"
    output_path.write_text(content)
    print(f"📄 Saved to: {output_path}")

    # Extract and save code block
    import re
    code_blocks = re.findall(r'```python(.*?)```', content, re.DOTALL)
    print(f"\n📦 Found {len(code_blocks)} code blocks")

    if code_blocks:
        test_code = code_blocks[-1].strip()  # Get last block (most complete)
        test_path = Path(__file__).parent.parent / "tests" / "unit" / "entity" / "test_agent_team_comprehensive.py"
        test_path.write_text(test_code + "\n")
        print(f"✅ Saved test_agent_team_comprehensive.py ({len(test_code)} chars)")

if __name__ == "__main__":
    main()
