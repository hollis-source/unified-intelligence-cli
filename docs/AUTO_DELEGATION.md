# Automatic Delegation to Auggie (GPT-5)

This repository enables automatic delegation of complex, high–token-cost tasks from Claude Code to Auggie (GPT-5) using a UserPromptSubmit hook.

## How it works
- Hook: `.claude/hooks/auto_delegate.py`
- Registered in `.claude/settings.json` under `hooks.UserPromptSubmit` after `ultrathink_submit.py`
- On each user prompt, the hook:
  1) Scores task complexity (0–10) via rule‑based heuristics
  2) Decides: delegate | suggest | keep
  3) When delegating, prepends a directive instructing Claude to call the MCP tool `mcp__auggie__auggie_with_gpt5` with a JSON payload that includes working directory, context, constraints, and deliverables
  4) Logs the decision to `~/.claude/delegation.log`

## Delegation criteria
Delegates if the prompt contains indicators of token-heavy work:
- Research/analysis/docs (e.g., "research", "compare", "best practices", "write a guide")
- Large code generation (e.g., ">100 lines", "create module", "scaffold")
- Multi-file/cross‑cutting changes (e.g., "refactor across", ">3 files", "entire project")
- Test suite generation (e.g., "write tests", "test suite")
- Complex debugging (e.g., "stack trace", "bottleneck", "race condition")

Keeps with Claude for:
- Simple reads (“read”, “show me”, “what’s in…”) and quick edits (“fix typo”, “<10 lines”) 
- Status checks (“git status”) and short Q&A

## Configuration
- DELEGATION_DISABLE=1 — disables the hook
- DELEGATION_MODE=aggressive|balanced|conservative — sets thresholds
  - aggressive: auto≥5, suggest≥3
  - balanced: auto≥7, suggest≥4 (default)
  - conservative: auto≥8, suggest≥5
- DELEGATION_THRESHOLD=<int> — overrides auto threshold

## Safety & edge cases
- Single‑message opt‑out: include `no-delegate` in the prompt
- Recursion prevention: hook marks delegated prompts with `[DELEGATED_BY_AUTO_DELEGATE]` and skips if present
- If user already requests Auggie (e.g., "use auggie"), the hook does not force delegation
- Fallback: directive instructs Claude to proceed itself if Auggie MCP is unavailable

## Logging
- Appends newline‑delimited JSON to `~/.claude/delegation.log`:
  - `{ ts, decision, score, reasons, mode, threshold, len_chars, len_lines }`

## Example
Prompt: "Research Redis security best practices and write a guide"
- Score: 9 → decision: delegate
- Claude prepends delegation directive and calls `mcp__auggie__auggie_with_gpt5`
- Auggie performs work; Claude summarizes concisely

## Overriding behavior
- Per‑message: add `no-delegate`
- Global: `export DELEGATION_DISABLE=1`

## Troubleshooting
- No delegation happening:
  - Check `.claude/settings.json` includes `auto_delegate.py` after `ultrathink_submit.py`
  - Ensure the hook script is executable with `python3`
  - Verify env vars and that your prompt matches delegation criteria
- Too many delegations:
  - Set `DELEGATION_MODE=conservative` or increase `DELEGATION_THRESHOLD`
- Logs missing:
  - Ensure `~/.claude` directory is writable

## Token savings
Complex tasks typically incur 50–70% Claude token savings by shifting research, long codegen, and multi‑file edits to Auggie. Simple tasks remain on Claude to preserve responsiveness.
