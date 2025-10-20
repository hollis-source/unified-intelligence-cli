#!/usr/bin/env python3
"""Generate Task entity tests using Qwen3 (Phase 2)."""

import os
from pathlib import Path
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("QWEN_ENDPOINT"),
    api_key=os.getenv("HF_TOKEN")
)

# Read Task source
task_source = """
@dataclass
class Task:
    description: str
    priority: int = 1
    task_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
"""

prompt = f"""Generate pytest tests for Task entity. CONCISE. NO LONG THINKING.

Task source:
{task_source}

Generate test_task_comprehensive.py with 15+ tests:
- test_task_creation_minimal (description only)
- test_task_creation_full (all parameters)
- test_task_default_priority (verify priority=1 default)
- test_task_default_task_id (verify None default)
- test_task_default_dependencies (verify empty list default)
- test_task_with_dependencies (multiple dependencies)
- @pytest.mark.parametrize for edge cases (empty description, high priority, etc.)

Imports: from src.entities.agent import Task
         import pytest

OUTPUT ONLY ```python block:"""

print("🤖 Generating Task tests...")

response = client.chat.completions.create(
    model="Qwen/Qwen3-Next-80B-A3B-Instruct",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=2000,
    temperature=0.1
)

content = response.choices[0].message.content
print(content)
print("\n" + "=" * 80)

# Extract and save
import re
matches = re.findall(r'```python(.*?)```', content, re.DOTALL)
if matches:
    code = matches[-1].strip()
    out_path = Path("tests/unit/entity/test_task_comprehensive.py")
    out_path.write_text(code + "\n")
    print(f"✅ Saved {len(code)} chars to {out_path}")
else:
    print("⚠️  No code block found")
    Path("ai_development/p2_testing/phase2_task_raw.txt").write_text(content)
