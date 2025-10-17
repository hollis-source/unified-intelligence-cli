#!/usr/bin/env python3
"""Quick Phase 2 test generation with less thinking."""

import os
from pathlib import Path
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("QWEN_ENDPOINT"),
    api_key=os.getenv("HF_TOKEN")
)

# Load source
agent_team_source = Path("src/entity/agent_team.py").read_text()[:2000]

prompt = f"""Generate pytest tests for AgentTeam entity. NO THINKING. CODE ONLY.

SOURCE:
```python
{agent_team_source}
```

Generate test_agent_team_comprehensive.py with:
- 15+ test functions
- Test creation, route_internally(), get_agent(), can_handle(), get_all_capabilities()
- Use parametrize for routing scenarios

Imports:
from src.entity.agent_team import AgentTeam
from src.entities.agent import Agent, Task
import pytest

OUTPUT ONLY ```python CODE BLOCK:"""

print("🤖 Generating (direct mode)...")

response = client.chat.completions.create(
    model="Qwen/Qwen3-Next-80B-A3B-Instruct",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=3000,
    temperature=0.1
)

content = response.choices[0].message.content
print(content)

# Save
import re
matches = re.findall(r'```python(.*?)```', content, re.DOTALL)
if matches:
    code = matches[-1].strip()
    out_path = Path("tests/unit/entity/test_agent_team_comprehensive.py")
    out_path.write_text(code + "\n")
    print(f"\n✅ Saved {len(code)} chars to {out_path}")
else:
    print(f"\n⚠️  No code block found. Saving raw output...")
    Path("ai_development/p2_testing/phase2_raw.txt").write_text(content)
