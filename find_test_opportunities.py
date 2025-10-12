#!/usr/bin/env python3
"""Identify high-value test opportunities for Project Builder on syd2 codebase."""

import asyncio
from src.adapters.mcp.paramiko_ssh_adapter import create_paramiko_ssh_adapter

async def main():
    adapter = create_paramiko_ssh_adapter(default_host="syd2.jacobhollis.com")
    await adapter.connect()
    
    base_path = "/opt/grokmonster/cna-dad-release-v1.0/src"
    
    # Candidate files to inspect
    candidates = [
        f"{base_path}/services/grok_client.py",
        f"{base_path}/services/memory_consolidation.py",
        f"{base_path}/services/relevance_scorer.py",
        f"{base_path}/config.py",
        f"{base_path}/main.py",
    ]
    
    print("=" * 70)
    print("SCANNING SYD2 CODEBASE FOR TEST OPPORTUNITIES")
    print("=" * 70)
    print()
    
    for file_path in candidates:
        try:
            content = await adapter.read_file("syd2.jacobhollis.com", file_path)
            lines = content.split('\n')
            total_lines = len(lines)
            
            # Analyze for common issues
            bare_excepts = sum(1 for line in lines if line.strip() == 'except:')
            missing_type_hints = sum(1 for line in lines if line.strip().startswith('def ') and '->' not in line)
            long_functions = sum(1 for i, line in enumerate(lines) if line.strip().startswith('def ') and 
                                any(lines[j].strip().startswith('def ') for j in range(i+1, min(i+51, len(lines)))))
            missing_docstrings = sum(1 for i, line in enumerate(lines) if line.strip().startswith('def ') and 
                                    (i+1 >= len(lines) or '"""' not in lines[i+1]))
            
            print(f"📄 {file_path.split('/')[-1]}")
            print(f"   Lines: {total_lines}")
            print(f"   Bare except blocks: {bare_excepts}")
            print(f"   Functions missing type hints: {missing_type_hints}")
            print(f"   Functions missing docstrings: {missing_docstrings}")
            
            # Show first 10 function definitions
            func_defs = [line for line in lines[:200] if line.strip().startswith('def ')][:5]
            if func_defs:
                print(f"   First few functions:")
                for func in func_defs:
                    print(f"      - {func.strip()}")
            print()
            
        except Exception as e:
            print(f"✗ Error reading {file_path}: {e}\n")
    
    await adapter.disconnect()
    
    print("=" * 70)
    print("RECOMMENDED TEST SCENARIOS:")
    print("=" * 70)
    print()
    print("1. ✅ COMPLETED: Fix bare except blocks in db_status.py")
    print()
    print("2. 🎯 Add type hints to grok_client.py functions")
    print("   Goal: 'Add type hints to all functions in /opt/grokmonster/.../grok_client.py'")
    print()
    print("3. 🎯 Add docstrings to memory_consolidation.py")
    print("   Goal: 'Add comprehensive docstrings to all functions in /opt/grokmonster/.../memory_consolidation.py'")
    print()
    print("4. 🎯 Refactor long functions in relevance_scorer.py")
    print("   Goal: 'Refactor functions longer than 50 lines in /opt/grokmonster/.../relevance_scorer.py'")
    print()

if __name__ == "__main__":
    asyncio.run(main())
