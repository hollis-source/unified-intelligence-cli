#!/usr/bin/env python3
"""Fix extracted code from JSON wrapper."""

import re
import json

# Read the corrupted file
with open('tests/unit/entity/category_theory/test_morphism_comprehensive.py', 'r') as f:
    content = f.read()

# Try to extract from JSON-like structure
# The structure is: [{'role': 'assistant', 'content': '```python\nCODE\n```'}]

# Find the content field
pattern = r"\{'role': 'assistant', 'content': '(.*)'\}\]"
match = re.search(pattern, content, re.DOTALL)

if match:
    extracted = match.group(1)

    # Unescape common patterns
    extracted = extracted.replace('\\n', '\n')
    extracted = extracted.replace('\\\\', '\\')
    extracted = extracted.replace("\\'", "'")
    extracted = extracted.replace('\\"', '"')

    # Remove markdown code blocks if present
    if '```python' in extracted:
        extracted = extracted.split('```python\n', 1)[1]
        if '\n```' in extracted:
            extracted = extracted.rsplit('\n```', 1)[0]

    print(f'✅ Extraction successful: {len(extracted)} characters')
    print(f'   Lines: {len(extracted.splitlines())}')

    # Verify it looks like Python
    if 'import pytest' in extracted and 'def test_' in extracted:
        print('✅ Looks like valid Python code')

        # Write clean version
        with open('tests/unit/entity/category_theory/test_morphism_comprehensive.py', 'w') as f:
            f.write(extracted)
        print('✅ File rewritten successfully')
    else:
        print('❌ Extracted content does not look like Python')
        print(f'First 200 chars: {extracted[:200]}')
else:
    print('❌ Could not find pattern')
    print(f'First 500 chars of file: {content[:500]}')
