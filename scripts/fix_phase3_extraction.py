#!/usr/bin/env python3
"""Fix Phase 3 test extraction - extract code from malformed output."""

import re
from pathlib import Path

project_root = Path(__file__).parent.parent
test_file = project_root / "tests/unit/entity/test_agent_team_comprehensive.py"

# Read the malformed output
with open(test_file, 'r') as f:
    content = f.read()

# Extract Python code from markdown blocks
pattern = r'```python\s*\n(.*?)\n```'
matches = re.findall(pattern, content, re.DOTALL)

if matches:
    code = matches[0].strip()
    print(f"✅ Extracted {len(code)} characters of Python code")
    print(f"   Lines: {len(code.splitlines())}")

    # Write back the clean code
    with open(test_file, 'w') as f:
        f.write(code)

    print(f"✅ File rewritten successfully")
else:
    print("❌ No code blocks found")
