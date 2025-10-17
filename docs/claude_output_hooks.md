# Claude/Auggie Output Hooks

Deterministic, configuration-driven output behavior for assistant-facing rendering.

Precedence: CLI `--claude-settings` > ENV `CLAUDE_SETTINGS_PATH` > file `config/claude_settings.json` > safe defaults.

## Keys, types, defaults (production-safe)
- output.redact_thoughts: bool, default true
- output.thought_tag_names: array[string], default ["think"] (case-sensitive)
- output.verbosity: {quiet,normal,verbose,debug}, default normal
- output.max_chars: int, default 0 (unlimited)
- output.wrap_code_blocks: {none,fenced,augment_code_snippet}, default augment_code_snippet
- output.inline_code_allowed: bool, default true
- output.include_routing_trace: bool, default true
- output.show_top3_domain_scores: bool, default true (only when verbosity ∈ {verbose,debug})
- output.include_correlation_id: bool, default true
- output.show_cache_annotations: bool, default true
- docs.quickstart_pointer_enabled: bool, default true
- dogfooding.banner_enabled: bool, default true
- routing.trace_format: {human,json,both}, default both

## Behavior
- Thought redaction: remove content enclosed by tags listed in `thought_tag_names` when `redact_thoughts=true`.
- Verbosity gates: quiet (essentials only) → normal (standard) → verbose (include routing) → debug (add safe debug).
- Truncation: if `max_chars>0`, cap final output; never truncate inside a code fence or augment block.
- Code: wrap multi-line fenced blocks per `wrap_code_blocks` policy; inline backticks are allowed only when enabled.
- Routing trace: include only if metadata provided and `include_routing_trace=true`; honor `routing.trace_format`.
- Correlation ID: shown once at top when enabled and provided by host.
- Cache: append concise annotation when metadata provides cache hit/miss (and ttl if available).
- Pointers/Banners: optional one-line footer/banners when enabled.

## Examples
```json
{
  "output": {
    "redact_thoughts": true,
    "verbosity": "verbose",
    "wrap_code_blocks": "augment_code_snippet",
    "include_routing_trace": true,
    "show_top3_domain_scores": true,
    "max_chars": 0
  },
  "routing": { "trace_format": "json" }
}
```

## Using different settings
- CLI: `python -m src.main --task "..." --claude-settings config/claude_settings.json`
- ENV: `CLAUDE_SETTINGS_PATH=config/claude_settings.json python -m src.main --task "..."`

## Safety
- Redaction defaults to on; invalid/missing keys fall back to defaults.
- Hooks do not affect planning/execution semantics or tool behavior.

