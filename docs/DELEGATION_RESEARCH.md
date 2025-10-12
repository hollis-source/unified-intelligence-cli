# Delegation Research & Design Rationale

This document captures the research, criteria, and design decisions for automatically delegating complex tasks from Claude Code to Auggie (GPT-5) to minimize Claude token usage.

## Token usage patterns (observed/problem statement)
- High token consumption drivers:
  - Reading/processing long files or many files
  - Extensive multi-step reasoning (ultrathink)
  - Large code/document generation
  - Complex, open-ended research tasks
- Low token consumption tasks:
  - Short reads and quick edits
  - Simple status checks
  - Direct Q&A

## Delegation criteria
We use a transparent, rule-based scoring system (0–10) with explainable reasons:
- +3 Research/Docs terms: "research", "analyze", "compare", "best practices", "write a guide", "documentation"
- +3 Large generation terms: "generate", "create module", ">100 lines", "scaffold"
- +3 Multi-file/refactor terms: "refactor", "across", ">3 files", "entire project"
- +2 Tests terms: "write tests", "test suite", "integration tests"
- +3 Complex debugging: "stack trace", "bottleneck", "race condition"
- +3 Prompt length >1200 chars; +2 if >600
- +2 >60 lines; +1 >30 lines
- −3 Simple/quick indicators: "read", "show me", "git status", "fix typo", "<10 lines"

Decision bands (mode-dependent):
- Aggressive: auto≥5, suggest≥3
- Balanced: auto≥7, suggest≥4 (default)
- Conservative: auto≥8, suggest≥5

## Hook architecture
- Hook point: `UserPromptSubmit` (runs before prompt is sent)
- Order: `ultrathink_submit.py` → `auto_delegate.py`
- Behavior:
  1) Read prompt from stdin
  2) Check opt-outs: `DELEGATION_DISABLE=1` or `no-delegate` in prompt
  3) Prevent recursion via `[DELEGATED_BY_AUTO_DELEGATE]` marker
  4) Compute score and reasons
  5) Decision: delegate | suggest | keep
  6) If delegating, prepend directive instructing Claude to call MCP tool `mcp__auggie__auggie_with_gpt5` with a JSON instruction payload (includes repo path, context, constraints, deliverables)
  7) Log decision to `~/.claude/delegation.log`

## Prompt rewriting strategy
- Preserve original user intent verbatim
- Provide working directory and repo root
- Add constraints to minimize Claude token usage
- Define deliverables and success criteria
- Keep payload JSON (machine-parseable) to reduce misinterpretation

## Safety mechanisms
- Opt-out via env or prompt keyword
- Recursion prevention marker
- Fallback guidance if Auggie is unavailable (Claude proceeds and notes fallback)
- Logging for analysis and tuning

## Validation plan
Test prompts:
- Delegate:
  - "Research best practices for X and write a guide"
  - "Refactor the entire authentication system across 5 files"
  - "Generate comprehensive test suite for the API"
  - "Analyze performance bottlenecks and create optimization plan"
- Keep:
  - "Read src/main.py"
  - "Fix typo in line 42"
  - "What's the current git status?"
  - "Show me the error in logs"
- Edge cases:
  - Already mentions "use auggie"
  - `DELEGATION_DISABLE=1`
  - Ambiguous complexity

## Estimated token savings
- Research/docs: 70–95% savings (Auggie handles bulk content; Claude summarizes)
- Large codegen: 50–80% savings (Auggie generates; Claude integrates)
- Multi-file refactors: 50–70% savings (Auggie applies changes; Claude reviews)

## Future improvements
- Learn thresholds from observed logs (adaptive tuning)
- Detect file counts and sizes via quick repo scan for more accurate scoring
- Add PostToolUse hook to compress/trim verbose outputs automatically
- Consider NLP-based classifier if rule-based accuracy is insufficient

