# UI-CLI Integration Status

**Date**: 2025-09-30
**Current Version**: Week 3 Complete (Debug Flags Added)

---

## What is ui-cli?

`ui-cli` is the **user-facing command** for the Unified Intelligence CLI project. It's the entry point that orchestrates multi-agent task execution.

### Current Installation Methods

1. **Development Mode** (No installation):
   ```bash
   ./ui-cli --task "Your task" --provider mock
   ```

2. **Python Module** (No installation):
   ```bash
   python3 -m src.main --task "Your task" --provider mock
   ```

3. **Installed Command** (Requires venv):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .
   ui-cli --task "Your task" --provider mock
   ```

---

## Current UI-CLI Features (Week 3)

### ✅ Implemented
```bash
ui-cli --help
```

**Options**:
- `-t, --task TEXT` - Task description (multiple allowed)
- `--provider [mock|grok|tongyi]` - LLM provider selection
- `-v, --verbose` - Verbose output (INFO level)
- `--debug` - Debug output (DEBUG level) **← Week 3**
- `--parallel/--sequential` - Execution mode
- `--config PATH` - Config file path
- `--timeout INTEGER` - Timeout in seconds

### Example Usage

**Single Task (Mock Provider)**:
```bash
./ui-cli --task "Write a Python hello world function" --provider mock
```

**Multi-Task (With Verbose)**:
```bash
./ui-cli \
  --task "Write a factorial function" \
  --task "Write tests for factorial" \
  --provider mock \
  --verbose
```

**Debug Mode (Week 3 - Flag exists but no logs)**:
```bash
./ui-cli --task "Test debug" --provider tongyi --debug
# ⚠️  Currently shows no debug output (Week 4 will fix this)
```

---

## Week 4-6 Pipeline: Enhancing ui-cli

### WEEK 4: Debug Logging (Make --debug Useful)

**Current Problem**:
```bash
$ ./ui-cli --task "test" --provider tongyi --debug
========================================
Result #1
========================================
Status: success
Output: ...
# ⚠️  No HTTP logs, no tool logs, no agent selection logs
```

**After Week 4**:
```bash
$ ./ui-cli --task "test" --provider tongyi --debug
2025-09-30 15:30:01 - tongyi_adapter - DEBUG - [tongyi_adapter.py:85] - HTTP Request: http://localhost:8080/completion
2025-09-30 15:30:01 - tongyi_adapter - DEBUG - [tongyi_adapter.py:87] - Prompt: <|im_start|>system\nYou are a helpful assistant...
2025-09-30 15:30:02 - tongyi_adapter - DEBUG - [tongyi_adapter.py:95] - HTTP Response: 200 OK
2025-09-30 15:30:02 - tongyi_adapter - DEBUG - [tongyi_adapter.py:97] - Response content: {"content": "..."}
2025-09-30 15:30:02 - task_coordinator - DEBUG - [task_coordinator.py:42] - Selected agent: tester (match score: 0.85)
========================================
Result #1
========================================
Status: success
Output: ...
```

**Value**: Users can troubleshoot LLM failures, see API calls, debug agent selection.

---

### WEEK 5: Tool Calling (Enable Agents to Use Tools)

**Current Problem**:
```bash
$ ./ui-cli --task "List files in src/ directory" --provider tongyi
========================================
Result #1
========================================
Status: success
Output: I cannot list files, I can only generate text.
# ⚠️  Tongyi cannot use tools
```

**After Week 5**:
```bash
$ ./ui-cli --task "List files in src/ directory" --provider tongyi --debug
2025-09-30 15:35:01 - tongyi_adapter - DEBUG - Available tools: ['run_command', 'read_file_content', 'write_file_content', 'list_files']
2025-09-30 15:35:02 - tongyi_adapter - DEBUG - Tool call detected: list_files(directory='src/', pattern='*.py')
2025-09-30 15:35:02 - tools - DEBUG - Executing: list_files(directory='src/', pattern='*.py')
2025-09-30 15:35:02 - tools - DEBUG - Tool result: FILE       1245 main.py\nFILE       3456 config.py\n...
========================================
Result #1
========================================
Status: success
Output: Files in src/ directory:
- main.py (1245 bytes)
- config.py (3456 bytes)
...
Metadata: {'tools_used': ['list_files']}
```

**Value**: Agents can execute real tasks (run commands, read/write files, run tests).

---

### WEEK 6: E2E Validation (Full Agentic Workflows)

**Current Problem**:
- No end-to-end test with real LLM + coordinator + tools
- Unknown if multi-task coordination works with Tongyi
- Unknown performance characteristics

**After Week 6**:
```bash
$ ./ui-cli \
  --task "Write a Python function to sort a list" \
  --task "Write pytest tests for the function" \
  --task "Run the tests and report results" \
  --provider tongyi \
  --debug

2025-09-30 15:40:01 - task_coordinator - DEBUG - Coordinating 3 tasks with 5 agents
2025-09-30 15:40:01 - task_coordinator - DEBUG - Task 1 assigned to: coder
2025-09-30 15:40:03 - tongyi_adapter - DEBUG - Tool call: write_file_content(file_path='sort_list.py', ...)
2025-09-30 15:40:05 - task_coordinator - DEBUG - Task 2 assigned to: tester
2025-09-30 15:40:07 - tongyi_adapter - DEBUG - Tool call: write_file_content(file_path='test_sort_list.py', ...)
2025-09-30 15:40:09 - task_coordinator - DEBUG - Task 3 assigned to: tester
2025-09-30 15:40:11 - tongyi_adapter - DEBUG - Tool call: run_command(command='pytest test_sort_list.py')
========================================
Result #1
========================================
Status: success
Output: Created sort_list.py with bubble_sort() function
========================================
Result #2
========================================
Status: success
Output: Created test_sort_list.py with 5 test cases
========================================
Result #3
========================================
Status: success
Output: ======================== test session starts =========================
5 passed in 0.12s
Metadata: {'tools_used': ['write_file_content', 'run_command'], 'latency_ms': 2340}
```

**Value**: Production-ready multi-agent workflows with real LLM.

---

## Integration Points: ui-cli ↔ Week 4-6

### Week 4 Integration

**Files Modified** (all enhance ui-cli experience):
1. `src/adapters/llm/tongyi_adapter.py` - Logs HTTP requests when `--debug` flag used
2. `src/adapters/llm/grok_adapter.py` - Logs API calls when `--debug` flag used
3. `src/tools.py` - Logs command execution when `--debug` flag used
4. `src/use_cases/task_coordinator.py` - Logs agent selection when `--debug` flag used

**CLI Command Impact**:
```bash
# Before Week 4
./ui-cli --task "test" --debug
# → No debug output

# After Week 4
./ui-cli --task "test" --debug
# → Shows HTTP logs, tool logs, agent selection logs
```

---

### Week 5 Integration

**Files Modified**:
1. `src/adapters/llm/tongyi_adapter.py` - Implements IToolSupportedProvider
2. `src/interfaces/llm_provider.py` - Adds tool_registry to LLMConfig

**CLI Command Impact**:
```bash
# Before Week 5
./ui-cli --task "List files in src/" --provider tongyi
# → Tongyi responds: "I cannot execute commands"

# After Week 5
./ui-cli --task "List files in src/" --provider tongyi
# → Tongyi calls list_files tool, returns actual directory listing
```

**New Capabilities**:
- Agents can read files
- Agents can write files
- Agents can run shell commands
- Agents can list directories

---

### Week 6 Integration

**Files Modified**:
1. `scripts/test_e2e_tongyi_coordinator.py` - E2E test suite
2. `docs/TONGYI_EXAMPLES.md` - Real workflow examples
3. `README.md` - Updated with Tongyi as recommended provider

**CLI Command Impact**:
```bash
# Complex multi-task workflow (validated in Week 6)
./ui-cli \
  --task "Set up a Python project with: main.py, tests/, README.md" \
  --task "Write a function to calculate Fibonacci numbers" \
  --task "Write comprehensive tests" \
  --task "Run tests and ensure 100% coverage" \
  --provider tongyi \
  --parallel

# → Full agentic coordination with tools
# → Multiple agents working in parallel
# → Real files created, tests run, results reported
# → Performance metrics logged
```

---

## ui-cli Architecture Integration

```
User runs: ./ui-cli --task "..." --provider tongyi --debug
    ↓
main.py (CLI entry point)
    ↓
load_config() ← Loads debug flag from CLI
    ↓
setup_logging(verbose, debug) ← Week 4: Sets DEBUG level
    ↓
ProviderFactory.create_provider("tongyi") ← Creates TongyiAdapter
    ↓
compose_dependencies(llm_provider, agents, logger)
    ↓
TaskCoordinator.coordinate(tasks, agents)
    ↓ [Week 4 logging]
    ├─→ task_coordinator.py logs agent selection
    ↓
AgentExecutor.execute(agent, task)
    ↓ [Week 5 tool calling]
    ├─→ TongyiAdapter.generate_with_tools()
    │   ├─→ tongyi_adapter.py logs HTTP requests [Week 4]
    │   ├─→ Parses tool calls from response [Week 5]
    │   └─→ ToolRegistry.execute_tool()
    │       └─→ tools.py logs command execution [Week 4]
    ↓
ResultFormatter.format_results()
    ↓ [Week 2 - already done]
    └─→ Rich table output with error details
```

---

## Testing ui-cli with Week 4-6 Features

### Test 1: Debug Logging (Week 4)
```bash
./ui-cli --task "Simple test" --provider tongyi --debug 2>&1 | grep "DEBUG"
# Should show 5+ debug log lines
```

### Test 2: Tool Calling (Week 5)
```bash
./ui-cli --task "Create a file called hello.txt with content 'Hello World'" --provider tongyi
cat hello.txt
# Should contain: Hello World
```

### Test 3: Multi-Task Coordination (Week 6)
```bash
./ui-cli \
  --task "Write Python function: def add(a, b)" \
  --task "Write test: test_add()" \
  --task "Run pytest" \
  --provider tongyi \
  --parallel \
  --debug

# Should:
# - Create function file
# - Create test file
# - Run pytest
# - All with debug logs showing coordination
```

---

## Summary: ui-cli IS the Project

**Key Insight**: `ui-cli` is not a separate app—it's the **primary interface** for the unified-intelligence-cli project.

**Week 4-6 Pipeline Goals**:
1. **Week 4**: Make `--debug` flag useful (show logs)
2. **Week 5**: Make agents powerful (use tools)
3. **Week 6**: Validate production readiness (E2E tests)

**All improvements directly enhance the ui-cli user experience.**

---

## Next Steps

1. ✅ ui-cli wrapper created (`./ui-cli`)
2. ⏳ Proceed with Week 4: Add debug logging
3. ⏳ Proceed with Week 5: Add tool calling
4. ⏳ Proceed with Week 6: E2E validation

**User Command After Week 4-6**:
```bash
./ui-cli \
  --task "Your complex task" \
  --provider tongyi \
  --debug \
  --parallel
# → Full agentic workflow with tools, coordination, and visibility
```