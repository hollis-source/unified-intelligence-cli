#!/usr/bin/env python3
"""
Simple script to generate Phase 1 tests using Qwen3 via OpenAI-compatible API.
"""

import os
from pathlib import Path
from openai import OpenAI

def main():
    # Setup client for Qwen endpoint
    client = OpenAI(
        base_url=os.getenv("QWEN_ENDPOINT", "https://crlqq5n5zwaz4rnh.us-east-2.aws.endpoints.huggingface.cloud/v1"),
        api_key=os.getenv("HF_TOKEN")
    )

    # Load context files
    plan_path = Path(__file__).parent.parent / "docs" / "P2_TESTING_INTEGRATION_PLAN.md"
    plan_content = plan_path.read_text()[:3000]  # First 3000 chars

    agent_path = Path(__file__).parent.parent / "src" / "entity" / "agent.py"
    agent_source = agent_path.read_text()

    prompt = f"""ultrathink: Generate ATADO-specific pytest test infrastructure.

INTEGRATION PLAN (excerpt):
{plan_content}

ACTUAL AGENT SOURCE:
```python
{agent_source}
```

Generate TWO Python files in markdown code blocks:

1. tests/conftest.py - Pytest fixtures:
   - Use: from src.entity.agent import Agent, Task
   - Use: from unittest.mock import MagicMock
   - Fixtures: mock_text_generator, sample_agent, sample_task

2. tests/unit/entity/test_agent_comprehensive.py - 20+ tests:
   - Test Agent creation (role, capabilities, tier, parent_agent, specialization)
   - Test can_handle() with 0.6 threshold fuzzy matching
   - Use @pytest.mark.parametrize for multiple scenarios

Output ONLY code in ```python blocks. No explanations."""

    print("🤖 Calling Qwen3-Next-80B-A3B-Instruct...")
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
    output_path = Path(__file__).parent.parent / "ai_development" / "p2_testing" / "phase1_qwen_output.txt"
    output_path.write_text(content)
    print(f"📄 Saved to: {output_path}")

    # Extract and save code blocks
    import re
    code_blocks = re.findall(r'```python\s*\n(.*?)\n```', content, re.DOTALL)
    print(f"\n📦 Found {len(code_blocks)} code blocks")

    for i, block in enumerate(code_blocks, 1):
        block_path = output_path.parent / f"phase1_block_{i}.py"
        block_path.write_text(block.strip())
        print(f"   Block {i} → {block_path}")

if __name__ == "__main__":
    main()
