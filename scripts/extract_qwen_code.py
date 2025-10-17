#!/usr/bin/env python3
"""Extract code blocks from Qwen3 output and save to proper locations."""

import re
from pathlib import Path

# Read generated output
output_file = Path(__file__).parent.parent / "ai_development" / "p2_testing" / "phase1_generated.txt"
content = output_file.read_text()

# Extract code blocks
pattern = r'```python\s*\n#\s*(.*?)\s*\n(.*?)\n```'
matches = re.findall(pattern, content, re.DOTALL)

print(f"Found {len(matches)} code blocks\n")

for file_path_comment, code in matches:
    print(f"📄 {file_path_comment}")
    print(f"   {len(code)} characters")

    # Save to actual file location
    if "conftest" in file_path_comment:
        target = Path(__file__).parent.parent / "tests" / "conftest_generated.py"
    elif "test_agent_comprehensive" in file_path_comment:
        target = Path(__file__).parent.parent / "tests" / "unit" / "entity" / "test_agent_comprehensive.py"
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        print(f"   ⚠️  Unknown file path: {file_path_comment}")
        continue

    target.write_text(code.strip() + "\n")
    print(f"   ✅ Saved to: {target}\n")

print("\n✅ Code extraction complete!")
